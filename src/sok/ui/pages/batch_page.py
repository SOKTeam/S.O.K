# ===----------------------------------------------------------------------=== #
#
# This source file is part of the S.O.K open source project
#
# Copyright (c) 2026 S.O.K Team
# Licensed under the MIT License
#
# See LICENSE for license information
#
# ===----------------------------------------------------------------------=== #
"""Base page for batch renaming: movies, books, games and tracks.

Each item maps to its own online match. The page has three screens:

- empty: a sentence, what to drop, and a key to choose a folder;
- work: a sentence ("18 movies to sort."), the list of the items (FileRow)
  and, at the right, the scene of the selected item. When S.O.K needs an
  answer (several results, nothing found, or "This is not it"), the scene
  becomes a pick panel: search again and choose the result. At the bottom,
  the one main action with its count and shortcut, and the destination;
- done: what the rename did, with Undo and Open the folder.

Subclasses say what they search and how they name the files.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QScrollArea,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sok.config import get_config_manager
from sok.core.history import COPY, LINK
from sok.core.batch import (
    STATUS_AMBIGUOUS,
    STATUS_MISSING,
    BatchMatch,
    candidate_year,
    QueryParser,
    SameWork,
)
from sok.core.history import UndoReport
from sok.core.interfaces import ContentType, MediaType
from sok.core.media_manager import get_media_manager
from sok.file_operations.artwork import image_url
from sok.file_operations.mixins.parsing import FileParsingMixin
from sok.media.factory import create_media_item
from sok.ui import message_box
from sok.ui.components.base import KeyButton
from sok.ui.components.file_row import RowData
from sok.ui.components.organize.empty_state import EmptyFan, TagCloud
from sok.ui.components.organize.rename_summary import RenameSummary, SummaryData
from sok.ui.components.organize.media_list import (
    STATUS_DONE,
    STATUS_OK,
    STATUS_PENDING,
    Describe,
    Entry,
    GroupFiles,
    MediaList,
    describe_dated,
    one_item_per_file,
)
from sok.ui.components.organize.pick_panel import Choice, PickPanel
from sok.ui.components.scene import Scene, SceneItem, Shape
from sok.ui.components.search import load_poster
from sok.ui.controllers.default_paths import default_destination
from sok.ui.controllers.file_mode import hard_link_blocked
from sok.ui.controllers.ui_state import set_progress
from sok.ui.controllers.undo import undo_operation
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.i18n import tr, trn
from sok.ui.platform import IS_MACOS, request_attention
from sok.ui.motion import fade_in
from sok.ui.responsive import (
    LOW_HEIGHT,
    SidePanel,
    display_font,
    fit_display,
    side_width,
)
from sok.ui.theme import Theme, ui_font
from sok.ui.workers import BatchOrganizeWorker, BatchSearchWorker

logger = logging.getLogger(__name__)

# English texts of each kind of page: (key, one, other) for the sentences
# with a number, (key, text) for the others. The translations are in the
# language files.
KIND_TEXTS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "movies": {
        "title": ("batch_title_movies", "{n} movie to sort.", "{n} movies to sort."),
        "done": ("batch_done_movies", "{n} movie sorted.", "{n} movies sorted."),
        "empty_title": ("batch_empty_title_movies", "No movies to sort."),
        "empty_text": (
            "batch_empty_text_movies",
            "Drop a folder of movies here. S.O.K finds each title and its "
            "poster, then puts every movie in its own folder.",
        ),
        "action": ("batch_action_movies", "Sort the movies"),
        "pick": ("batch_pick_movies", "Which movie is it?"),
    },
    "series": {
        "title": (
            "batch_title_series",
            "{n} episode to sort.",
            "{n} episodes to sort.",
        ),
        "done": ("batch_done_series", "{n} episode sorted.", "{n} episodes sorted."),
        "empty_title": ("batch_empty_title_series", "No episodes to sort."),
        "empty_text": (
            "batch_empty_text_series",
            "Drop a folder of episodes here. S.O.K groups them by series, "
            "finds the title of each episode, then files them by season.",
        ),
        "action": ("batch_action_series", "Sort the episodes"),
        "pick": ("batch_pick_series", "Which series is it?"),
    },
    "books": {
        "title": ("batch_title_books", "{n} book to sort.", "{n} books to sort."),
        "done": ("batch_done_books", "{n} book sorted.", "{n} books sorted."),
        "empty_title": ("batch_empty_title_books", "No books to sort."),
        "empty_text": (
            "batch_empty_text_books",
            "Drop a folder of ebooks here. S.O.K finds each book, its author "
            "and its cover, then files it under its author.",
        ),
        "action": ("batch_action_books", "Sort the books"),
        "pick": ("batch_pick_books", "Which book is it?"),
    },
    "games": {
        "title": ("batch_title_games", "{n} game to sort.", "{n} games to sort."),
        "done": ("batch_done_games", "{n} game sorted.", "{n} games sorted."),
        "empty_title": ("batch_empty_title_games", "No games to sort."),
        "empty_text": (
            "batch_empty_text_games",
            "Drop a folder of ROMs or ISOs here. S.O.K recognizes the "
            "console, finds the title and the cover, then puts every game "
            "in its place.",
        ),
        "action": ("batch_action_games", "Sort the games"),
        "pick": ("batch_pick_games", "Which game is it?"),
    },
    "music": {
        "title": ("batch_title_music", "{n} track to sort.", "{n} tracks to sort."),
        "done": ("batch_done_music", "{n} track sorted.", "{n} tracks sorted."),
        "empty_title": ("batch_empty_title_music", "No music to sort."),
        "empty_text": (
            "batch_empty_text_music",
            "Drop your music here. S.O.K gathers the tracks into albums, finds "
            "each album and its cover, then files it under its artist.",
        ),
        "action": ("batch_action_music", "Sort the tracks"),
        "pick": ("batch_pick_music", "Which one is it?"),
    },
}

# Names of the services, as people know them.
SERVICE_NAMES = {
    "tmdb": "TMDB",
    "tvdb": "TVDB",
    "omdb": "OMDb",
    "imdb": "IMDb",
    "google_books": "Google Books",
    "openlibrary": "Open Library",
    "igdb": "IGDB",
    "rawg": "RAWG",
    "deezer": "Deezer",
    "spotify": "Spotify",
    "musicbrainz": "MusicBrainz",
    "lastfm": "Last.fm",
}

TMDB_SIZES = {"thumb": "w92", "scene": "w500"}


@dataclass
class _Run:
    """A rename in progress, as the page follows it.

    Attributes:
        worker: The worker, to stop it.
        started: time.monotonic() at the start.
        mode: File mode of the settings (move, link, copy).
        total: Number of files to move.
        total_bytes: Their size.
        owners: Each file to move, with the key of its item.
        by_name: Files not started yet, by name (the worker gives names).
        current: Key of the item being moved.
        current_file: File being moved.
        done_files: Files finished.
        done_bytes: Size of the files finished.
        sizes: Size of each file.
    """

    worker: Any
    started: float
    mode: str
    total: int
    total_bytes: int
    owners: Dict[Path, Path]
    by_name: Dict[str, List[Path]]
    sizes: Dict[Path, int]
    current: Optional[Path] = None
    current_file: Optional[Path] = None
    done_files: int = 0
    done_bytes: int = 0


# The website, until it has its own domain (see the release checklist).
SITE_URL = "https://sokfromsokteam.vercel.app"


def guide_url() -> str:
    """The user guide of the website: /guide in English, /<lang>/guide in
    the other languages of the app."""
    language = get_config_manager().get("language", "en")
    prefix = "" if language == "en" else f"/{language}"
    return f"{SITE_URL}{prefix}/guide"


def duration_text(seconds: float) -> str:
    """ "38 s", "2 min 10"."""
    seconds = max(0, round(seconds))
    if seconds < 60:
        return tr("batch_secs", "{s} s").format(s=seconds)
    return tr("batch_mins", "{m} min {s:02d}").format(m=seconds // 60, s=seconds % 60)


def sized_image_url(path: Optional[str], size: str) -> Optional[str]:
    """URL of an image of a result, small enough for its use.

    A TMDB path gets a size ("thumb" or "scene"); other services give a URL.
    """
    if path and path.startswith("/") and not path.startswith("//"):
        return f"https://image.tmdb.org/t/p/{TMDB_SIZES[size]}{path}"
    return image_url(path)


def shortcut_label(key: str) -> str:
    """The text of a Ctrl/Cmd shortcut, as the system writes it."""
    return f"⌘{key}" if IS_MACOS else f"Ctrl {key}"


def human_size(size: int) -> str:
    """A file size in the units of the language ("18.4 GB", "18,4 Go")."""
    if size >= 1024**3:
        value, key, default = size / 1024**3, "size_gb", "{0} GB"
    else:
        value, key, default = size / 1024**2, "size_mb", "{0} MB"
    number = f"{value:.1f}"
    if get_config_manager().get("language", "en") != "en":
        number = number.replace(".", ",")
    return tr(key, default).format(number)


def common_folder(files: List[Path]) -> Optional[Path]:
    """The folder holding all the files, or None if they share only the root."""
    if not files:
        return None
    try:
        common = Path(os.path.commonpath([str(f.parent) for f in files]))
    except ValueError:
        return None
    return common if len(common.parts) > 1 else None


def display_path(path: Path, limit: int = 48) -> str:
    """A path with the home folder written "~", shortened when too long.

    A long path keeps its last folders: "…/Downloads/Movies".
    """
    home = Path.home()
    try:
        text = "~/" + str(path.relative_to(home)) if path != home else "~"
    except ValueError:
        text = str(path)
    if len(text) <= limit:
        return text
    parts = Path(text).parts
    tail = ""
    for part in reversed(parts):
        candidate = f"{part}/{tail}" if tail else part
        if len(candidate) + 2 > limit:
            break
        tail = candidate
    return f"…/{tail or parts[-1]}"


@dataclass(frozen=True)
class SearchSpec:
    """How the items of a kind are searched and turned into media items."""

    content_type: ContentType
    parse: Any
    same_work: Optional[Any]
    localized: bool
    factory_type: str


@dataclass
class PageSummary:
    """What the home page shows of a media page.

    Attributes:
        total: Items to sort, counted as the page counts them (files for
            series and music).
        ready: Of them, recognized.
        waiting: Of them, to pick or not found.
        size: Bytes of all the files.
        covers: (thumbnail or None, title) of the first items.
    """

    total: int = 0
    ready: int = 0
    waiting: int = 0
    size: int = 0
    covers: List[Tuple[Optional[QPixmap], str]] = field(default_factory=list)


class _Destination:
    """The folder the items go to (what the destination drop zone was)."""

    def __init__(self) -> None:
        self._path: Optional[Path] = None

    def get_path(self) -> Optional[Path]:
        return self._path

    def set_path(self, path: Optional[Path]) -> None:
        self._path = Path(path) if path else None


class _Screen(QWidget):
    """A screen of the page: transparent, the window paints its background
    and the light of the scene (see main_window.LightColumn)."""


class BatchPage(QWidget):
    """Page for batch renaming, configured by its subclasses.

    Subclasses set the class attributes and implement make_ops() and
    organize_method().

    Signals:
        history_requested: The user wants to see the history.

    Attributes:
        kind: Key of the texts of the page (see KIND_TEXTS).
        scene_shape: How the selected item stands on the scene.
        default_path_type: Media type of the default destination folder
            ("video", "book"…).
        media_type: Media type whose selected API is searched.
        content_type: What to search.
        factory_type: Content type given to create_media_item().
        parse: Reads the file name of an item.
        same_work: Tells when several results are one work.
        localized: Ask for results in the language of the app.
        describe: Text of a candidate in the pick list.
        group_files: Splits added files into items.
        show_quality: Show the quality read from the file names.
    """

    history_requested = Signal()
    # The light of the page moved: the window paints it again.
    light_changed = Signal()

    kind = "movies"
    scene_shape = Shape.POSTER
    # Shape of the empty places of the empty screen (scene_shape if None).
    empty_shape: Optional[Shape] = None
    default_path_type = "video"
    media_type = MediaType.VIDEO
    content_type = ContentType.MOVIE
    factory_type = "movie"
    parse: QueryParser
    same_work: Optional[SameWork] = None
    localized = True
    describe: Describe = staticmethod(describe_dated)
    group_files: GroupFiles = staticmethod(one_item_per_file)
    show_quality = False
    # Cover tiles in a grid instead of rows (albums).
    grid = False
    # Start the line under the title with the folder of the files.
    show_found_in = True
    # Size the thumbnails of the list are loaded at.
    thumb_size = (72, 108)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the page."""
        super().__init__(parent)
        self.setObjectName("Page")
        self._ops = self.make_ops()
        self._manager = get_media_manager()
        self._files: List[Path] = []
        self._search_runner = WorkerRunner(self)
        self._rescan_runner = WorkerRunner(self)
        self._organize_runner = WorkerRunner(self)
        self._search_queue: List[Tuple[SearchSpec, List[List[Path]]]] = []
        self._sizes: Dict[Path, int] = {}
        self._dest_drop = _Destination()
        self._images: Dict[str, QPixmap] = {}
        # Key of the item shown in the pick panel, or None for the scene.
        self._picking: Optional[Path] = None
        self._searching: set[Path] = set()
        self._last_report: Optional[Dict[str, Any]] = None
        # "idle", "running" (a rename is going on) or "end" (it is over and
        # the list shows what each item became).
        self._phase = "idle"
        self._run: Optional[_Run] = None

        self._build()
        self._apply_default_destination()

    # ------------------------------------------------------- Subclass hooks

    def make_ops(self) -> Any:
        """Return the file operations of the media type."""
        raise NotImplementedError

    def organize_method(self) -> Callable[..., Dict[str, Any]]:
        """Return the method of the file operations that moves the files."""
        raise NotImplementedError

    def page_title(self) -> str:
        """Name of the media type, for the window title."""
        return tr("movies", "Movies")

    def query_placeholder(self) -> str:
        """Hint shown in an empty search field."""
        return ""

    def preview_name(self, item: Any, file: Path) -> str:
        """New name of an item's first file."""
        return self._ops.generate_new_filename(item, file.name)

    def nothing_ready_text(self) -> str:
        """Message when no item is ready."""
        return tr("nothing_ready", "No file is ready to rename.")

    def summary(self, covers: int = 3) -> PageSummary:
        """Counts, size and first covers of the items, for the home page."""
        result = PageSummary()
        for entry in self._list.entries():
            if entry.status == STATUS_DONE:
                continue
            count = self.count_of(entry)
            result.total += count
            if entry.status == STATUS_OK and entry.candidate:
                result.ready += count
            elif entry.status in (STATUS_AMBIGUOUS, STATUS_MISSING):
                result.waiting += count
            for file in entry.files:
                if file not in self._sizes:
                    try:
                        self._sizes[file] = file.stat().st_size
                    except OSError:
                        self._sizes[file] = 0
                result.size += self._sizes[file]
            if len(result.covers) < covers:
                data = self._row_data(entry)
                result.covers.append((data.thumbnail, data.title))
        return result

    def search_spec(self, files: Optional[List[Path]] = None) -> SearchSpec:
        """How the item of these files is searched: the class attributes,
        unless a page searches its items in several ways (albums and tracks)."""
        return SearchSpec(
            self.content_type,
            self.parse,
            self.same_work,
            self.localized,
            self.factory_type,
        )

    def count_of(self, entry: Entry) -> int:
        """How much an item counts in the sentences: 1, or its files."""
        return 1

    def lead_prefix(self, entries: List[Entry]) -> List[str]:
        """Sentences put first in the line under the title."""
        return []

    def row_detail(self, entry: Entry) -> Optional[QWidget]:
        """What the selected row shows under it (None for nothing)."""
        return None

    def scene_subtitle(self, item: Any, candidate: Dict[str, Any]) -> str:
        """The muted line under the title on the scene: year and author."""
        year = getattr(item, "year", None) or candidate_year(candidate)
        return " · ".join(str(x) for x in (year, self.item_author(item)) if x)

    def scene_destination(self, entry: Entry) -> str:
        """The final path shown under "Will be stored here"."""
        dest = self._dest_drop.get_path()
        return str(dest / entry.new_name) if dest and entry.new_name else ""

    def item_author(self, item: Any) -> str:
        """Author, artist or platform written after the title."""
        for attr in ("author", "artist"):
            value = getattr(item, attr, "")
            if value:
                return str(value)
        return ""

    # ---------------------------------------------------------------- Texts

    def _text(self, name: str, n: Optional[int] = None) -> str:
        spec = KIND_TEXTS[self.kind][name]
        if n is not None:
            return trn(spec[0], n, spec[1], spec[2])
        return tr(spec[0], spec[1])

    # ------------------------------------------------------------------ UI

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._screens = QStackedWidget()
        outer.addWidget(self._screens)

        self._empty = self._build_empty()
        self._work = self._build_work()
        for screen in (self._empty, self._work):
            self._screens.addWidget(screen)

        rename = QShortcut(QKeySequence("Ctrl+R"), self)
        rename.activated.connect(self._on_rename_shortcut)
        choose = QShortcut(QKeySequence("Ctrl+O"), self)
        choose.activated.connect(self._browse_sources)
        for key, step in ((Qt.Key.Key_Down, 1), (Qt.Key.Key_Up, -1)):
            move = QShortcut(QKeySequence(key), self)
            move.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            move.activated.connect(lambda s=step: self._list.select_next(s))

        self.setAcceptDrops(True)
        self.retranslateUi()
        self._show_screen()

    def _build_empty(self) -> QWidget:
        """The empty screen of mockup 05, centered: three empty places, the
        title, what to drop, the keys, and what S.O.K recognizes."""
        screen = _Screen()
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)
        layout.addStretch(1)
        center = Qt.AlignmentFlag.AlignHCenter
        self._empty_fan = EmptyFan(self.empty_shape or self.scene_shape)
        layout.addWidget(self._empty_fan, 0, center)
        layout.addSpacing(28)
        self._empty_title = QLabel()
        self._empty_title.setFont(self._display_font())
        self._empty_title.setWordWrap(True)
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty_title)
        layout.addSpacing(28)
        self._empty_text = QLabel()
        self._empty_text.setFont(ui_font(17))
        self._empty_text.setWordWrap(True)
        self._empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Centered between stretches: a label added with an alignment does
        # not get the height of its wrapped lines.
        self._empty_text.setFixedWidth(520)
        text_row = QHBoxLayout()
        text_row.addStretch()
        text_row.addWidget(self._empty_text)
        text_row.addStretch()
        layout.addLayout(text_row)
        layout.addSpacing(28)
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addStretch()
        self._choose_btn = KeyButton("", primary=True)
        self._choose_btn.set_shortcut(shortcut_label("O"))
        self._choose_btn.clicked.connect(self._browse_sources)
        row.addWidget(self._choose_btn)
        self._guide_btn = KeyButton("")
        self._guide_btn.clicked.connect(self._open_guide)
        row.addWidget(self._guide_btn)
        row.addStretch()
        layout.addLayout(row)
        layout.addSpacing(48)
        self._known_lbl = QLabel()
        known = ui_font(11, 600)
        known.setLetterSpacing(known.SpacingType.AbsoluteSpacing, 0.88)
        known.setCapitalization(known.Capitalization.AllUppercase)
        self._known_lbl.setFont(known)
        self._known_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._known_lbl)
        layout.addSpacing(12)
        self._known_tags = TagCloud()
        layout.addWidget(self._known_tags, 0, center)
        layout.addStretch(1)
        return screen

    def known_tags(self) -> Tuple[str, List[str]]:
        """What the empty screen lists under its keys: a label and tags.

        By default the formats the page accepts ("14 formats accepted":
        MKV, MP4…). The games page lists the consoles instead.
        """
        formats = list(
            dict.fromkeys(
                ext.lstrip(".").upper() for ext in self._ops.supported_extensions
            )
        )
        label = trn(
            "batch_formats_accepted",
            len(formats),
            "{n} format accepted",
            "{n} formats accepted",
        )
        return label, formats

    def _open_guide(self) -> None:
        """The user guide of the website, in the language of the app."""
        QDesktopServices.openUrl(QUrl(guide_url()))

    def _build_work(self) -> QWidget:
        screen = _Screen()
        columns = QHBoxLayout(screen)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(0)

        left = QVBoxLayout()
        left.setContentsMargins(26, 40, 26, 24)
        left.setSpacing(0)
        head = QVBoxLayout()
        head.setContentsMargins(14, 0, 14, 0)
        head.setSpacing(10)
        self._kicker = QLabel()
        kicker = ui_font(11, 600)
        kicker.setLetterSpacing(kicker.SpacingType.AbsoluteSpacing, 0.88)
        kicker.setCapitalization(kicker.Capitalization.AllUppercase)
        self._kicker.setFont(kicker)
        self._kicker.setVisible(False)
        self._kicker_tone = "ink-faint"
        head.addWidget(self._kicker)
        self._title_lbl = QLabel()
        self._title_lbl.setFont(self._display_font())
        self._title_lbl.setWordWrap(True)
        head.addWidget(self._title_lbl)
        self._lead_lbl = QLabel()
        self._lead_lbl.setFont(ui_font(17))
        self._lead_lbl.setWordWrap(True)
        self._lead_lbl.setTextFormat(Qt.TextFormat.RichText)
        head.addWidget(self._lead_lbl)
        left.addLayout(head)
        left.addSpacing(28)

        self._list = MediaList(
            self._phased_row,
            file_extensions=self._ops.supported_extensions,
            describe=self.describe,
            group_files=self.group_files,
            make_detail=self.row_detail,
            grid=self.grid,
        )
        self._list.row_changed.connect(self._refresh_previews_and_action)
        self._list.row_rescan_requested.connect(self._rescan_row)
        self._list.files_added.connect(self._on_files_added)
        self._list.current_changed.connect(self._on_current_changed)
        self._list.row_action.connect(self._on_row_action)
        left.addWidget(self._list, 1)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(4)
        self._progress.setVisible(False)
        self._progress.setTextVisible(False)
        self._progress.setObjectName("Progress")
        left.addWidget(self._progress)
        self._progress_label = QLabel("")
        self._progress_label.setObjectName("EmptyState")
        self._progress_label.setVisible(False)
        left.addWidget(self._progress_label)
        left.addSpacing(16)

        actions = QHBoxLayout()
        actions.setContentsMargins(14, 0, 14, 0)
        actions.setSpacing(12)
        self._action_btn = KeyButton("", primary=True)
        self._action_btn.set_shortcut(shortcut_label("R"))
        self._action_btn.setEnabled(False)
        self._action_btn.clicked.connect(self._start_rename)
        actions.addWidget(self._action_btn)
        self._dest_btn = KeyButton("")
        self._dest_btn.clicked.connect(self._choose_destination)
        actions.addWidget(self._dest_btn)
        self._stop_btn = KeyButton("")
        self._stop_btn.clicked.connect(self._stop_rename)
        self._stop_btn.setVisible(False)
        actions.addWidget(self._stop_btn)
        self._run_lbl = QLabel()
        self._run_lbl.setVisible(False)
        actions.addSpacing(4)
        actions.addWidget(self._run_lbl)
        actions.addStretch()
        left.addLayout(actions)
        left.addSpacing(12)
        self._dest_lbl = QLabel()
        self._dest_lbl.setFont(ui_font(13))
        self._dest_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._dest_lbl.setWordWrap(True)
        self._dest_lbl.setContentsMargins(14, 0, 14, 0)
        left.addWidget(self._dest_lbl)
        columns.addLayout(left, 1)

        self._right = QStackedWidget()
        self._right.setFixedWidth(side_width(1440))
        self._scene = Scene()
        self._not_it_btn = self._scene.add_action()
        self._not_it_btn.clicked.connect(self._open_picker)
        self._leave_btn = self._scene.add_action()
        self._leave_btn.clicked.connect(self._leave_current)
        self._picker = PickPanel()
        self._picker.search.connect(self._on_picker_search)
        self._picker.chosen.connect(self._on_picker_chosen)
        self._picker.cancelled.connect(self._close_picker)
        # Scrolls when the window is too low for the poster and the details.
        self._scene_scroll = QScrollArea()
        self._scene_scroll.setWidgetResizable(True)
        self._scene_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scene_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scene_scroll.setWidget(self._scene)
        self._summary = RenameSummary()
        self._summary.open_clicked.connect(self._open_destination)
        self._summary.undo_clicked.connect(self._undo_last)
        # Scrolls when the window is too low for the covers and the figures.
        self._summary_scroll = QScrollArea()
        self._summary_scroll.setWidgetResizable(True)
        self._summary_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._summary_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._summary_scroll.setWidget(self._summary)
        self._right.addWidget(self._scene_scroll)
        self._right.addWidget(self._picker)
        self._right.addWidget(self._summary_scroll)
        # Beside the list, or over it in a narrow window.
        self._panel = SidePanel(
            screen, columns, self._right, lambda: tr("back_to_list", "List")
        )
        self._list.row_clicked.connect(lambda _key: self._panel.open())
        # The window paints the light of the scene or of the summary.
        for source, scroll in (
            (self._scene, self._scene_scroll),
            (self._summary, self._summary_scroll),
        ):
            scroll.viewport().setStyleSheet("background: transparent;")
            source.light_changed.connect(self.light_changed.emit)
            scroll.verticalScrollBar().valueChanged.connect(self.light_changed.emit)
        self._right.currentChanged.connect(lambda _i: self.light_changed.emit())
        return screen

    @staticmethod
    def _display_font():
        return display_font(1440)

    def resizeEvent(self, e):  # noqa: N802 - Qt API
        """The right column, the big titles and the empty places follow the
        size of the page."""
        super().resizeEvent(e)
        self._panel.fit(self.width())
        inline = not self._panel.narrow
        self._scene.inline_light = self._summary.inline_light = inline
        self.light_changed.emit()
        self._right.setFixedWidth(self._panel.column_width(self.width()))
        self._fit_scene()
        fit_display([self._title_lbl, self._empty_title], self.width())
        self._empty_text.setFixedWidth(min(520, max(280, self.width() - 80)))
        self._empty_fan.setVisible(self.height() >= LOW_HEIGHT)

    def _palette(self) -> Dict[str, str]:
        return getattr(self.window(), "c", None) or Theme.DARK

    def _restyle(self) -> None:
        c = self._palette()
        for label, role in (
            (self._empty_title, "ink"),
            (self._empty_text, "ink-muted"),
            (self._known_lbl, "ink-faint"),
            (self._title_lbl, "ink"),
            (self._lead_lbl, "ink-muted"),
            (self._dest_lbl, "ink-muted"),
            (self._kicker, self._kicker_tone),
        ):
            label.setStyleSheet(f"color: {c[role]}; background: transparent;")
        self._run_lbl.setStyleSheet(
            f"color: {c['ink-muted']}; background: transparent;"
            f" font-family: '{Theme.MONO}'; font-size: 13px;"
        )

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            self._restyle()

    def _show_screen(self) -> None:
        """Show the empty screen or the list."""
        self._screens.setCurrentWidget(
            self._work if self._list.has_rows() else self._empty
        )
        self.light_changed.emit()

    # ----------------------------------------------------------------- I/O

    def showEvent(self, event) -> None:
        """Apply the default destination set in the settings since startup."""
        self._apply_default_destination()
        self._restyle()
        super().showEvent(event)

    def _apply_default_destination(self) -> None:
        if self._dest_drop.get_path() is None:
            self._dest_drop.set_path(default_destination(self.default_path_type))
            self._update_destination()

    def stop_workers(self) -> None:
        """Stop any running worker."""
        self._search_runner.stop()
        self._rescan_runner.stop()
        self._organize_runner.stop()

    def retranslateUi(self) -> None:
        """Refresh translatable labels."""
        self._empty_title.setText(self._text("empty_title"))
        self._empty_text.setText(self._text("empty_text"))
        self._choose_btn.setText(tr("batch_choose_folder", "Choose a folder"))
        self._guide_btn.setText(tr("batch_how_it_works", "How it works"))
        label, tags = self.known_tags()
        self._known_lbl.setText(label)
        self._known_tags.set_tags(tags)
        self._action_btn.setText(self._text("action"))
        self._dest_btn.setText(tr("batch_change_folder", "Change folder"))
        self._scene.set_destination_label(
            tr("batch_will_go_here", "Will be stored here")
        )
        self._not_it_btn.setText(tr("batch_not_it", "This is not it"))
        self._leave_btn.setText(tr("batch_leave_file", "Leave this file"))
        self._picker.set_texts(
            self._text("pick"),
            self.query_placeholder() or tr("movie_title_year", "Title (optional year)"),
            tr("batch_cancel", "Cancel"),
        )
        self._list.set_was_label(tr("batch_was", "was"))
        self._stop_btn.setText(tr("batch_stop", "Stop"))
        self._summary.open_btn.setText(tr("batch_open_folder", "Open the folder"))
        self._summary.undo_btn.setText(tr("batch_undo_rename", "Undo the renaming"))
        self._summary.note.setText(
            tr("batch_undo_note", "Every file can go back exactly where it was.")
        )
        self._update_summary()
        self._update_destination()
        self._panel.retranslate()
        self._on_current_changed(self._list.current())

    # ------------------------------------------------------------- Sources

    def load_files(self, files: List[Path]) -> None:
        """Add files found elsewhere, such as on the home page, and search them.

        Args:
            files: Files to add; those already in the list are skipped.
        """
        self._on_files_added(self._list.add_files(files))

    def _browse_sources(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, tr("select_folder_dialog", "Add folder")
        )
        if folder:
            self._list.add_paths([Path(folder)])

    def dragEnterEvent(self, event):  # noqa: N802 - Qt API
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802 - Qt API
        self._list.add_paths([Path(u.toLocalFile()) for u in event.mimeData().urls()])
        event.acceptProposedAction()

    def _on_files_added(self, items: List[List[Path]]) -> None:
        """Run a batch search on newly added items only."""
        if not items:
            return
        if self._phase == "end":
            self._back_to_idle()
        self._files = self._list.files()
        self._show_screen()
        self._update_summary()
        self._refresh_action_state()
        self._start_batch_search(items)

    # ---------------------------------------------------------- Destination

    def _choose_destination(self) -> None:
        start = str(self._dest_drop.get_path() or "")
        folder = QFileDialog.getExistingDirectory(
            self, tr("select_folder", "Select a folder"), start
        )
        if folder:
            self._dest_drop.set_path(Path(folder))
            self._update_destination()
            self._refresh_previews_and_action()

    def _update_destination(self) -> None:
        dest = self._dest_drop.get_path()
        c = self._palette()
        if dest:
            path = (
                f"<span style='font-family: \"Geist Mono\"; color: {c['ink']}'>"
                f"{display_path(dest)}</span>"
            )
            text = tr("batch_to", "To {path}.").format(path=path)
            waiting = sum(
                len(e.files)
                for e in self._list.entries()
                if e.status in (STATUS_AMBIGUOUS, STATUS_MISSING)
            )
            if waiting:
                text += " " + trn(
                    "batch_unknown_stays",
                    waiting,
                    "The unrecognized file stays where it is.",
                    "The {n} unrecognized files stay where they are.",
                )
        else:
            text = tr("batch_no_destination", "Choose where to store them.")
        self._dest_lbl.setText(text)

    def _open_destination(self) -> None:
        dest = self._dest_drop.get_path()
        if dest and dest.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(dest)))

    # ------------------------------------------------------------ Searching

    def _start_batch_search(self, items: Optional[List[List[Path]]] = None) -> None:
        target = items if items is not None else self._list.items()
        if not target:
            return
        for item in target:
            self._list.set_row_loading(item[0])
        # One search per way of searching, one after the other.
        by_spec: Dict[SearchSpec, List[List[Path]]] = {}
        for item in target:
            by_spec.setdefault(self.search_spec(item), []).append(item)
        self._search_queue = list(by_spec.items())
        self._set_progress(True, tr("searching", "Searching..."), 0)
        self._run_next_search()

    def _run_next_search(self) -> None:
        spec, items = self._search_queue.pop(0)
        worker = BatchSearchWorker(
            items,
            self.media_type,
            spec.content_type,
            spec.parse,
            same_work=spec.same_work,
            localized=spec.localized,
        )
        self._search_runner.run(
            worker,
            self._on_batch_search_done,
            self._on_search_error,
            self._on_search_progress,
        )

    def _on_search_progress(self, percent: int, filename: str) -> None:
        self._set_progress(True, filename, percent)

    def _on_batch_search_done(self, results: List[BatchMatch]) -> None:
        self._list.apply_results(results)
        if self._search_queue:
            self._run_next_search()
        else:
            self._set_progress(False)
        self._refresh_previews_and_action()

    def _on_search_error(self, error: str) -> None:
        self._search_queue = []
        self._set_progress(False)
        self._list.fail_pending()
        self._update_summary()
        message_box.warning(
            self,
            tr("error", "Error"),
            f"{tr('search_failed', 'Search failed:')} {error}",
        )

    def _rescan_all(self) -> None:
        self._files = self._list.files()
        self._start_batch_search()

    def _rescan_row(self, key: Path, query: str) -> None:
        files = self._list.item_files(key)
        if not query or not files:
            return
        self._searching.add(key)
        self._refresh_picker()
        spec = self.search_spec(files)
        worker = BatchSearchWorker(
            [files],
            self.media_type,
            spec.content_type,
            spec.parse,
            query,
            same_work=spec.same_work,
            localized=spec.localized,
        )
        self._rescan_runner.run(
            worker,
            self._on_row_search_done,
            lambda err, f=files, q=query: self._on_row_search_error(f, q, err),
        )

    def _on_row_search_done(self, results: List[BatchMatch]) -> None:
        for result in results:
            self._searching.discard(result.file)
            # A new search asks for a choice: nothing is Ready by itself.
            if result.candidates:
                result.status = STATUS_AMBIGUOUS
            self._list.apply_search_result(result)
        self._refresh_previews_and_action()
        self._refresh_picker()

    def _on_row_search_error(self, files: List[Path], query: str, error: str) -> None:
        logger.warning("Row rescan failed for %s: %s", files[0].name, error)
        self._searching.discard(files[0])
        self._list.apply_search_result(BatchMatch(files, query, None))
        self._refresh_previews_and_action()
        self._refresh_picker()
        message_box.warning(
            self,
            tr("error", "Error"),
            f"{tr('search_failed', 'Search failed:')} {error}",
        )

    # ------------------------------------------------------------- Display

    def _media_item(
        self, candidate: Optional[Dict[str, Any]], files: Optional[List[Path]] = None
    ) -> Any:
        """The media item of a result, for the files of its item."""
        if not candidate:
            return None
        lang = get_config_manager().get("language", "en")
        factory = self.search_spec(files).factory_type
        return create_media_item(candidate, factory, self._manager, language=lang)

    def _image(
        self, url: Optional[str], key: Path, width: int, height: int
    ) -> Optional[QPixmap]:
        """A loaded image, or None; loads it and redraws the item when ready."""
        if not url:
            return None
        if url in self._images:
            return self._images[url]

        source: str = url

        def loaded(pixmap: QPixmap, u: str = source, k: Path = key) -> None:
            self._images[u] = pixmap
            self._list.refresh_row(k)
            if k == self._list.current():
                self._show_scene(k)

        load_poster(url, width, height, self, loaded)
        return None

    def _phased_row(self, entry: Entry) -> RowData:
        """The row of an item, with where it is in a rename."""
        data = self._row_data(entry)
        data.phase = entry.phase
        if entry.phase == "waiting":
            data.state = tr("batch_state_waiting", "waiting")
        elif entry.phase == "current":
            mode = self._run.mode if self._run else "move"
            key, default = {
                COPY: ("batch_state_copy", "copying…"),
                LINK: ("batch_state_link", "linking…"),
            }.get(mode, ("batch_state_move", "moving…"))
            data.state = tr(key, default)
        elif entry.phase == "done":
            data.state = tr("batch_state_done", "sorted")
            data.line, data.line_tone = entry.moved_to, "ink-muted"
        elif entry.phase == "stays":
            data.state = tr("batch_state_stays", "stays here")
            if self._phase == "end":
                data.action = tr("batch_action_pick", "Pick")
        elif entry.phase == "failed":
            data.state = tr("batch_state_failed", "did not move")
            data.line, data.line_tone = entry.reason, "danger"
            data.action = tr("batch_action_retry", "Retry")
        return data

    def _row_data(self, entry: Entry) -> RowData:
        """What the row of an item shows."""
        was = entry.files[0].name
        if len(entry.files) > 1:
            was += f"  +{len(entry.files) - 1}"
        tags = self._quality_tags(entry.files[0]) if self.show_quality else []
        if entry.status == STATUS_PENDING:
            return RowData(entry.query or entry.files[0].stem, was, tags=tags)
        item = self._media_item(entry.candidate, entry.files)
        if item is None:
            return RowData(
                tr("batch_unknown", "Unknown title"),
                was,
                by=entry.query,
                tags=tags,
                unknown=True,
            )
        url = sized_image_url(getattr(item, "poster_url", None), "thumb")
        year = getattr(item, "year", None)
        return RowData(
            item.title,
            was,
            year=str(year) if year else "",
            by=self.item_author(item),
            tags=tags,
            confidence=entry.confidence,
            thumbnail=self._image(url, entry.key, *self.thumb_size),
        )

    def _quality_tags(self, file: Path) -> List[str]:
        info = FileParsingMixin.extract_quality_metadata(file.name)
        tags = [info.get("quality"), info.get("audio")]
        return [t for t in tags if t][:2]

    def _on_current_changed(self, key: Optional[Path]) -> None:
        entry = self._list.entry(key)
        if self._phase == "running":
            # The scene follows the file being moved.
            return
        if self._phase == "end" and (entry is None or entry.status == STATUS_DONE):
            self._right.setVisible(True)
            self._right.setCurrentWidget(self._summary_scroll)
            return
        if entry is None:
            self._right.setVisible(False)
            return
        self._right.setVisible(True)
        needs_answer = entry.status in (STATUS_AMBIGUOUS, STATUS_MISSING)
        if needs_answer or self._picking == key:
            self._picking = key
            self._right.setCurrentWidget(self._picker)
            self._refresh_picker()
        else:
            self._picking = None
            self._right.setCurrentWidget(self._scene_scroll)
            self._show_scene(entry.key)

    def _show_scene(self, key: Path) -> None:
        entry = self._list.entry(key)
        if entry is None:
            return
        item = self._media_item(entry.candidate, entry.files)
        if item is None:
            self._scene.set_item(
                SceneItem(
                    entry.query or entry.files[0].stem,
                    entry.files[0].name,
                    shape=self.scene_shape,
                    fields=self._fields(entry, None),
                )
            )
            self._fit_scene()
            return
        year = getattr(item, "year", None) or candidate_year(entry.candidate or {})
        subtitle = self.scene_subtitle(item, entry.candidate or {})
        url = sized_image_url(getattr(item, "poster_url", None), "scene")
        destination = self.scene_destination(entry)
        self._scene.set_item(
            SceneItem(
                item.title,
                subtitle,
                image=self._image(url, key, 456, 684),
                year=str(year or ""),
                shape=self.scene_shape,
                fields=self._fields(entry, item),
                destination=destination,
            )
        )
        self._fit_scene()

    def light_source(self) -> Any:
        """The scene or the summary beside the list, whichever the right
        column shows, for the window to paint its light; None otherwise."""
        if self._panel.narrow or self._screens.currentWidget() is not self._work:
            return None
        if not self._right.isVisible():
            return None
        current = self._right.currentWidget()
        if current is self._scene_scroll:
            return self._scene
        if current is self._summary_scroll:
            return self._summary
        return None

    def _fit_scene(self) -> None:
        """The poster of the scene gets smaller in a low window."""
        self._scene.fit_height(self._scene_scroll.viewport().height())

    def _fields(self, entry: Entry, item: Any) -> List[Tuple[str, str]]:
        """Rows of the dotted sheet: what S.O.K knows without opening files."""
        fields: List[Tuple[str, str]] = []
        if self.show_quality:
            info = FileParsingMixin.extract_quality_metadata(entry.files[0].name)
            quality = " · ".join(
                v
                for v in (info.get("quality"), info.get("codec"), info.get("audio"))
                if v
            )
            if quality:
                fields.append((tr("batch_quality", "Quality"), quality))
        formats = sorted(
            {f.suffix.lstrip(".").upper() for f in entry.files if f.suffix}
        )
        if formats:
            fields.append((tr("batch_format", "Format"), ", ".join(formats)))
        size = sum(f.stat().st_size for f in entry.files if f.exists())
        if size:
            fields.append((tr("batch_size", "Size"), human_size(size)))
        if len(entry.files) > 1:
            fields.append((tr("batch_files", "Files"), str(len(entry.files))))
        if item is not None:
            api = self._manager.current_apis.get(self.media_type, "")
            fields.append(
                (
                    tr("batch_found_with", "Recognized via"),
                    SERVICE_NAMES.get(api, api.upper()),
                )
            )
        return fields

    # ----------------------------------------------------------- Pick panel

    def _open_picker(self) -> None:
        key = self._list.current()
        if key is None:
            return
        self._picking = key
        self._right.setCurrentWidget(self._picker)
        fade_in(self._picker)
        self._refresh_picker()
        self._picker.focus_search()

    def _close_picker(self) -> None:
        key = self._picking
        self._picking = None
        entry = self._list.entry(key)
        if entry is not None and entry.status == STATUS_OK:
            self._right.setCurrentWidget(self._scene_scroll)
            fade_in(self._scene_scroll)
            self._show_scene(entry.key)
        else:
            # Nothing chosen yet: go to the next item.
            self._list.select_next()

    def _refresh_picker(self) -> None:
        entry = self._list.entry(self._picking)
        if entry is None:
            return
        choices = []
        for index, candidate in enumerate(entry.candidates):
            item = self._media_item(candidate, entry.files)
            year = getattr(item, "year", None) if item else None
            author = self.item_author(item) if item else ""
            choices.append(
                Choice(
                    item.title if item else self.describe(candidate),
                    " · ".join(str(x) for x in (year, author) if x),
                    sized_image_url(getattr(item, "poster_url", None), "thumb")
                    if item
                    else None,
                    current=index == entry.selected and entry.status == STATUS_OK,
                )
            )
        if entry.key in self._searching:
            status = tr("searching", "Searching...")
        elif not entry.candidates:
            status = tr("batch_nothing_found", "Nothing found for “{0}”.").format(
                entry.query
            )
        else:
            status = ""
        self._picker.show_item(
            f"{tr('batch_was', 'was')} {entry.files[0].name}",
            entry.query,
            choices,
            status,
        )

    def _on_picker_search(self, query: str) -> None:
        if self._picking is not None:
            self._list.request_search(self._picking, query)

    def _on_picker_chosen(self, index: int) -> None:
        key = self._picking
        if key is None:
            return
        self._picking = None
        self._list.choose(key, index)
        self._right.setCurrentWidget(self._scene_scroll)
        fade_in(self._scene_scroll)
        self._show_scene(key)

    def _leave_current(self) -> None:
        """Take the item out of the list; its files stay where they are."""
        key = self._list.current()
        if key is None:
            return
        self._list.remove_files(self._list.item_files(key))
        self._files = self._list.files()
        self._show_screen()
        self._update_summary()
        self._refresh_action_state()

    # ------------------------------------------------------------- Preview

    def _compute_new_name(self, files: List[Path], candidate: Dict[str, Any]) -> str:
        item = self._media_item(candidate, files)
        if item is None:
            return ""
        return self.preview_name(item, files[0])

    def _refresh_previews_and_action(self) -> None:
        for entry in self._list.entries():
            # Picked after a rename: ready to sort like any other item.
            if entry.phase == "stays" and entry.status == STATUS_OK:
                entry.phase = ""
        self._list.update_new_names(self._compute_new_name)
        self._update_summary()
        self._refresh_action_state()
        key = self._list.current()
        if key is not None and self._right.currentWidget() is self._scene_scroll:
            self._show_scene(key)

    def _refresh_action_state(self) -> None:
        ready = sum(
            self.count_of(e)
            for e in self._list.entries()
            if e.status == STATUS_OK and e.candidate
        )
        self._action_btn.set_count(ready if ready else None)
        has_dest = self._dest_drop.get_path() is not None
        self._action_btn.setEnabled(bool(ready) and has_dest)
        # While renaming, Stop takes its place; after, it comes back only
        # when something new is ready (an item just picked, a retry).
        self._action_btn.setVisible(
            self._phase == "idle" or (self._phase == "end" and bool(ready))
        )
        # After a rename, Open the folder is the one primary key.
        self._action_btn.set_primary(self._phase == "idle")

    def _update_summary(self) -> None:
        entries = [e for e in self._list.entries() if e.status != STATUS_DONE]
        counts: Dict[str, int] = {}
        for entry in entries:
            counts[entry.status] = counts.get(entry.status, 0) + self.count_of(entry)
        total = sum(counts.values())
        if self._phase != "idle":
            # The rename writes the title and the lead.
            if self._phase == "end":
                set_count = getattr(self.window(), "set_nav_count", None)
                if set_count is not None:
                    set_count(self, total)
            return
        self._title_lbl.setText(self._text("title", total))
        parts = []
        folder = common_folder(self._list.files()) if self.show_found_in else None
        if folder is not None:
            c = self._palette()
            parts.append(
                tr("batch_found_in", "Found in {path}.").format(
                    path=f"<span style='font-family: \"Geist Mono\"; color: {c['ink']}'>"
                    f"{display_path(folder)}</span>"
                )
            )
        parts.extend(self.lead_prefix(entries))
        pending = counts.get(STATUS_PENDING, 0)
        if pending:
            parts.append(
                trn(
                    "batch_searching",
                    pending,
                    "{n} being searched.",
                    "{n} being searched.",
                )
            )
        else:
            ready = counts.get(STATUS_OK, 0)
            waiting = counts.get(STATUS_AMBIGUOUS, 0) + counts.get(STATUS_MISSING, 0)
            if ready:
                parts.append(
                    trn("batch_recognized", ready, "{n} recognized.", "{n} recognized.")
                )
            if waiting:
                parts.append(
                    trn(
                        "batch_waiting",
                        waiting,
                        "{n} waits for your answer.",
                        "{n} wait for your answer.",
                    )
                )
        self._lead_lbl.setText(" ".join(parts))
        set_count = getattr(self.window(), "set_nav_count", None)
        if set_count is not None:
            set_count(self, total)

    # -------------------------------------------------------------- Rename

    def _on_rename_shortcut(self) -> None:
        if (
            self._action_btn.isVisible()
            and self._action_btn.isEnabled()
            and self._screens.currentWidget() is self._work
        ):
            self._start_rename()

    def _start_rename(self) -> None:
        """Rename the Ready items now: no question, it can be stopped and
        undone."""
        dest = self._dest_drop.get_path()
        if not dest or not Path(dest).exists():
            message_box.warning(
                self,
                tr("warning", "Warning"),
                tr("select_dest_warning", "Please select a destination folder."),
            )
            return

        mappings: List[Tuple[Path, Any]] = []
        owners: Dict[Path, Path] = {}
        for entry in self._list.entries():
            if entry.status != STATUS_OK or not entry.candidate:
                continue
            item = self._media_item(entry.candidate, entry.files)
            if item is None:
                continue
            mappings.extend((file, item) for file in entry.files)
            for file in entry.files:
                owners[file] = entry.key
        if not mappings:
            message_box.information(self, tr("info", "Info"), self.nothing_ready_text())
            return
        if hard_link_blocked(self, [file for file, _ in mappings], str(dest)):
            return

        sizes: Dict[Path, int] = {}
        by_name: Dict[str, List[Path]] = {}
        for file, _item in mappings:
            try:
                sizes[file] = file.stat().st_size
            except OSError:
                sizes[file] = 0
            by_name.setdefault(file.name, []).append(file)
        for entry in self._list.entries():
            if entry.key in owners.values():
                entry.phase, entry.reason = "waiting", ""
            elif entry.status != STATUS_DONE:
                entry.phase = "stays"
        worker = BatchOrganizeWorker(mappings, str(dest), self.organize_method())
        self._run = _Run(
            worker=worker,
            started=time.monotonic(),
            mode=get_config_manager().get("file_mode", "move"),
            total=len(mappings),
            total_bytes=sum(sizes.values()),
            owners=owners,
            by_name=by_name,
            sizes=sizes,
        )
        # Only the item being moved is lit while renaming; the list shows the
        # progress, so a narrow window closes the column.
        self._list.set_current(None)
        self._panel.close()
        self._set_phase("running")
        self._list.refresh_rows()
        worker.file_started.connect(self._on_file_started)
        self._organize_runner.run(
            worker, self._on_organize_done, self._on_organize_error
        )

    def _stop_rename(self) -> None:
        """Stop after the file being moved."""
        if self._run is not None:
            self._run.worker.request_stop()
            self._stop_btn.setEnabled(False)

    def _on_file_started(self, name: str, number: int, _total: int) -> None:
        """A file is about to move: the one before is done."""
        run = self._run
        if run is None:
            return
        if run.current_file is not None:
            run.done_bytes += run.sizes.get(run.current_file, 0)
        run.done_files = number - 1
        files = run.by_name.get(name) or []
        file = files.pop(0) if files else None
        key = run.owners.get(file) if file is not None else None
        if run.current is not None and run.current != key:
            previous = self._list.entry(run.current)
            dest = self._dest_drop.get_path()
            if previous is not None:
                previous.phase = "done"
                if previous.new_name and dest is not None:
                    previous.moved_to = self._shown_target(
                        str(dest / previous.new_name), dest
                    )
            self._list.refresh_row(run.current)
        run.current, run.current_file = key, file
        entry = self._list.entry(key)
        if entry is not None:
            entry.phase = "current"
            self._list.refresh_row(entry.key)
            self._show_scene(entry.key)
        self._show_run()

    def _show_run(self) -> None:
        """Title, lead, progress line and scene of a rename in progress."""
        run = self._run
        if run is None:
            return
        c = self._palette()
        done = self._text("done", run.done_files).rstrip(".")
        tail = tr("batch_of_total", "of {n}.").format(n=run.total)
        self._title_lbl.setText(
            f"{done} <span style='color: {c['ink-muted']}'>{tail}</span>"
        )
        dest = self._dest_drop.get_path()
        path = display_path(dest) if dest else ""
        lead_key, lead_default = {
            COPY: ("batch_lead_copy", "Copying to {path}."),
            LINK: ("batch_lead_link", "Linking into {path}."),
        }.get(run.mode, ("batch_lead_move", "Moving to {path}."))
        self._lead_lbl.setText(
            tr(lead_key, lead_default).format(path=path)
            + " "
            + tr(
                "batch_lead_go_on",
                "You can go to another page, the renaming goes on.",
            )
        )
        parts = [f"{run.done_files} / {run.total}"]
        if run.mode != LINK and run.done_bytes:
            key, default = (
                ("batch_bytes_copy", "{size} copied")
                if run.mode == COPY
                else ("batch_bytes_move", "{size} moved")
            )
            parts.append(tr(key, default).format(size=human_size(run.done_bytes)))
            elapsed = max(0.001, time.monotonic() - run.started)
            rate = run.done_bytes / elapsed
            parts.append(
                tr("batch_rate", "{size}/s").format(size=human_size(int(rate)))
            )
            left = (run.total_bytes - run.done_bytes) / rate if rate else 0
            parts.append(
                tr("batch_eta", "{time} left").format(time=duration_text(left))
            )
        self._run_lbl.setText(" · ".join(parts))
        set_count = getattr(self.window(), "set_nav_count", None)
        if set_count is not None:
            set_count(self, max(0, run.total - run.done_files))

    def _on_organize_done(self, report: Dict[str, Any]) -> None:
        run = self._run
        request_attention(self)
        self._last_report = report
        dest = self._dest_drop.get_path()
        moved = {Path(m["from"]): m.get("to", "") for m in report.get("moved", [])}
        failed: Dict[Path, str] = {}
        for error in report.get("errors", []):
            # "[Errno 16] Resource busy" → "Resource busy".
            text = re.sub(r"^\[Errno \d+\]\s*", "", str(error.get("error", "")))
            failed[Path(str(error.get("file", "")))] = text
        for skip in report.get("skipped", []):
            failed[Path(str(skip.get("file", "")))] = tr(
                "batch_skip_exists", "A file with this name is already there."
            )
        first: List[Path] = []
        sorted_keys: List[Path] = []
        for entry in self._list.entries():
            if run is None or entry.key not in run.owners.values():
                if entry.phase == "stays":
                    first.append(entry.key)
                continue
            reasons = [failed[f] for f in entry.files if f in failed]
            targets = [moved[f] for f in entry.files if f in moved]
            if reasons:
                entry.phase, entry.reason = "failed", reasons[0]
                first.append(entry.key)
            elif targets:
                entry.phase, entry.status = "done", STATUS_DONE
                entry.moved_to = self._shown_target(targets[0], dest)
                sorted_keys.append(entry.key)
            else:
                # Not reached: the rename was stopped before it.
                entry.phase = ""
        self._set_phase("end")
        self._list.put_first(first)
        self._list.refresh_rows()
        self._show_end(report, sorted_keys)

    def _shown_target(self, target: str, dest: Optional[Path]) -> str:
        """The new path, from the destination folder ("Films/Dune (2021)/…")."""
        path = Path(target)
        if dest is not None:
            try:
                return str(Path(dest.name) / path.relative_to(dest))
            except ValueError:
                pass
        return str(path)

    def _show_end(self, report: Dict[str, Any], sorted_keys: List[Path]) -> None:
        """Title, lead and summary of the rename that just ended."""
        run = self._run
        success = report.get("success", 0)
        seconds = time.monotonic() - run.started if run else 0
        at = datetime.now().strftime("%H:%M")
        if report.get("stopped"):
            self._set_kicker(tr("batch_stopped_at", "Stopped at {0}").format(at))
        else:
            self._set_kicker(tr("batch_done_at", "Done at {0}").format(at))
        self._title_lbl.setText(self._text("done", success))
        entries = self._list.entries()
        stays = sum(len(e.files) for e in entries if e.phase == "stays")
        failed = sum(len(e.files) for e in entries if e.phase == "failed")
        waiting = sum(
            len(e.files) for e in entries if e.status == STATUS_OK and not e.phase
        )
        parts: List[str] = []
        if stays:
            parts.append(
                trn(
                    "batch_end_stays",
                    stays,
                    "{n} file still waits for you: pick what it is.",
                    "{n} files still wait for you: pick what they are.",
                )
            )
        if failed:
            parts.append(
                trn(
                    "batch_end_failed",
                    failed,
                    "{n} file could not move.",
                    "{n} files could not move.",
                )
            )
        if waiting:
            parts.append(
                trn(
                    "batch_end_not_reached",
                    waiting,
                    "{n} file was not sorted yet.",
                    "{n} files were not sorted yet.",
                )
            )
        if not parts:
            parts.append(tr("batch_end_all", "Everything is sorted."))
        self._lead_lbl.setText(" ".join(parts))

        dest = self._dest_drop.get_path()
        moved_bytes = sum(
            (run.sizes.get(Path(m["from"]), 0) for m in report.get("moved", []))
            if run
            else []
        )
        fields = [
            (tr("batch_sum_sorted", "Sorted"), str(success)),
            (tr("batch_sum_time", "Time"), duration_text(seconds)),
        ]
        if run and run.mode != LINK and moved_bytes:
            key, default = (
                ("batch_sum_copied", "Copied")
                if run.mode == COPY
                else ("batch_sum_moved", "Moved")
            )
            fields.append((tr(key, default), human_size(moved_bytes)))
        tones: Dict[str, str] = {}
        if stays + failed:
            label = tr("batch_sum_left", "Left in place")
            fields.append((label, str(stays + failed)))
            tones[label] = "caution"
        if dest:
            fields.append(
                (tr("batch_sum_destination", "Destination"), display_path(dest, 28))
            )
        covers = []
        for sorted_key in sorted_keys[:3]:
            entry = self._list.entry(sorted_key)
            if entry is not None:
                data = self._row_data(entry)
                covers.append((data.thumbnail, data.title))
        self._summary.show_data(
            SummaryData(
                covers=covers,
                square=self.grid,
                fields=fields,
                tones=tones,
                can_undo=bool(report.get("operation")),
            )
        )
        self._list.set_current(None)
        # The summary comes in once, at the end: a fade and a small rise.
        self._summary.arrive()
        # In a narrow window the summary comes over the list.
        self._panel.open()
        self._update_destination()
        self._dest_lbl.setText(
            tr(
                "batch_end_note",
                "Drop more files to go on. The sorted lines then leave the list.",
            )
        )
        self._update_summary()
        self._refresh_action_state()

    def _on_row_action(self, key: Path) -> None:
        """The key of a row: pick what it is, or try the rename again."""
        entry = self._list.entry(key)
        if entry is None:
            return
        if entry.phase == "failed":
            self._start_rename()
        else:
            self._list.set_current(key)
            self._panel.open()

    def _back_to_idle(self) -> None:
        """Leave the end of a rename: the sorted items leave the list."""
        done = [
            f for e in self._list.entries() if e.status == STATUS_DONE for f in e.files
        ]
        self._list.remove_files(done)
        self._list.clear_phases()
        self._set_phase("idle")
        self._files = self._list.files()
        self._show_screen()
        self._update_summary()
        self._update_destination()
        self._refresh_action_state()
        self._on_current_changed(self._list.current())

    def _undo_last(self) -> None:
        operation = (self._last_report or {}).get("operation")
        if operation:
            undo_operation(
                self, self._organize_runner, operation, on_done=self._on_undone
            )

    def _on_undone(self, report: UndoReport) -> None:
        """Put the files back in the list, to rename them again."""
        self._last_report = None
        self._back_to_idle()
        self.load_files([Path(move.source) for move in report.restored])
        self._show_screen()

    def _on_organize_error(self, error: str) -> None:
        request_attention(self)
        self._list.clear_phases()
        self._set_phase("idle")
        self._update_summary()
        self._refresh_action_state()
        message_box.critical(
            self,
            tr("error", "Error"),
            f"{tr('error_prefix', 'Error:')} {error}",
        )

    def _set_kicker(self, text: str, tone: str = "ink-faint") -> None:
        self._kicker.setText(text)
        self._kicker.setVisible(bool(text))
        self._kicker_tone = tone
        self._restyle()

    def _set_phase(self, phase: str) -> None:
        """Show the keys and texts of a phase: idle, running or end."""
        self._phase = phase
        running = phase == "running"
        self._stop_btn.setVisible(running)
        self._stop_btn.setEnabled(True)
        self._run_lbl.setVisible(running)
        self._dest_btn.setVisible(phase == "idle")
        self._scene.set_actions_visible(not running)
        if running:
            self._set_kicker(tr("batch_running", "Renaming"), "accent-text")
            self._dest_lbl.setText(
                tr(
                    "batch_stop_note",
                    "Stop finishes the file in progress. What is already "
                    "sorted stays sorted, and can be undone from History.",
                )
            )
            self._scene.set_label(tr("batch_in_progress", "In progress"), "accent-text")
            self._right.setCurrentWidget(self._scene_scroll)
            self._right.setVisible(True)
            self._show_run()
        else:
            self._scene.set_label("")
        if phase == "idle":
            self._set_kicker("")
            self._run = None
        self._refresh_action_state()

    # -------------------------------------------------------------- Helpers

    def _set_progress(
        self,
        visible: bool,
        message: Optional[str] = None,
        value: Optional[int] = None,
    ) -> None:
        set_progress(self._progress, self._progress_label, visible, message, value)

    def closeEvent(self, event):
        """Stop background workers on close."""
        self.stop_workers()
        super().closeEvent(event)
