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
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QScrollArea,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sok.config import get_config_manager
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
from sok.ui.components.base import KeyButton, parse_color
from sok.ui.components.file_row import RowData
from sok.ui.components.organize.done_screen import DoneData, DoneScreen, StatData
from sok.ui.components.organize.media_list import (
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
    "tracks": {
        "title": ("batch_title_tracks", "{n} track to sort.", "{n} tracks to sort."),
        "done": ("batch_done_tracks", "{n} track sorted.", "{n} tracks sorted."),
        "empty_title": ("batch_empty_title_tracks", "No tracks to sort."),
        "empty_text": (
            "batch_empty_text_tracks",
            "Drop single tracks here. S.O.K finds the title, the artist and "
            "the album of each one, then files it with its album.",
        ),
        "action": ("batch_action_tracks", "Sort the tracks"),
        "pick": ("batch_pick_tracks", "Which track is it?"),
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


class _Destination:
    """The folder the items go to (what the destination drop zone was)."""

    def __init__(self) -> None:
        self._path: Optional[Path] = None

    def get_path(self) -> Optional[Path]:
        return self._path

    def set_path(self, path: Optional[Path]) -> None:
        self._path = Path(path) if path else None


class _Screen(QWidget):
    """A screen of the page, painted with the window background."""

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = getattr(self.window(), "c", None) or Theme.DARK
        p = QPainter(self)
        p.fillRect(self.rect(), parse_color(c["bg"]))
        p.end()


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

    kind = "movies"
    scene_shape = Shape.POSTER
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
        self._dest_drop = _Destination()
        self._images: Dict[str, QPixmap] = {}
        # Key of the item shown in the pick panel, or None for the scene.
        self._picking: Optional[Path] = None
        self._searching: set[Path] = set()
        self._rename_started = 0.0
        self._last_report: Optional[Dict[str, Any]] = None

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

    def rename_confirm_text(self, count: int) -> str:
        """Question asked before renaming count files."""
        return tr("rename_confirm_files", "Rename {0} file(s)?").format(count)

    def nothing_ready_text(self) -> str:
        """Message when no item is ready."""
        return tr("nothing_ready", "No file is ready to rename.")

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
        year = getattr(item, "year", None)
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
        self._done = DoneScreen()
        self._done.continue_clicked.connect(self._leave_done)
        self._done.history_clicked.connect(self.history_requested.emit)
        self._done.open_clicked.connect(self._open_destination)
        self._done.undo_clicked.connect(self._undo_last)
        for screen in (self._empty, self._work, self._done):
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
        screen = _Screen()
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(40, 64, 40, 40)
        layout.setSpacing(0)
        self._empty_title = QLabel()
        self._empty_title.setFont(self._display_font())
        self._empty_title.setWordWrap(True)
        layout.addWidget(self._empty_title)
        layout.addSpacing(14)
        self._empty_text = QLabel()
        self._empty_text.setFont(ui_font(17))
        self._empty_text.setWordWrap(True)
        self._empty_text.setMaximumWidth(620)
        layout.addWidget(self._empty_text)
        layout.addSpacing(32)
        row = QHBoxLayout()
        self._choose_btn = KeyButton("", primary=True)
        self._choose_btn.set_shortcut(shortcut_label("O"))
        self._choose_btn.clicked.connect(self._browse_sources)
        row.addWidget(self._choose_btn)
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()
        return screen

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
            self._row_data,
            file_extensions=self._ops.supported_extensions,
            describe=self.describe,
            group_files=self.group_files,
            make_detail=self.row_detail,
        )
        self._list.row_changed.connect(self._refresh_previews_and_action)
        self._list.row_rescan_requested.connect(self._rescan_row)
        self._list.files_added.connect(self._on_files_added)
        self._list.current_changed.connect(self._on_current_changed)
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
        actions.addStretch()
        left.addLayout(actions)
        left.addSpacing(12)
        self._dest_lbl = QLabel()
        self._dest_lbl.setFont(ui_font(13))
        self._dest_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._dest_lbl.setContentsMargins(14, 0, 14, 0)
        left.addWidget(self._dest_lbl)
        columns.addLayout(left, 1)

        self._right = QStackedWidget()
        self._right.setFixedWidth(460)
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
        self._right.addWidget(self._scene_scroll)
        self._right.addWidget(self._picker)
        columns.addWidget(self._right)
        return screen

    @staticmethod
    def _display_font():
        font = ui_font(52, 650)
        font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, -2.08)
        return font

    def _palette(self) -> Dict[str, str]:
        return getattr(self.window(), "c", None) or Theme.DARK

    def _restyle(self) -> None:
        c = self._palette()
        for label, role in (
            (self._empty_title, "ink"),
            (self._empty_text, "ink-muted"),
            (self._title_lbl, "ink"),
            (self._lead_lbl, "ink-muted"),
            (self._dest_lbl, "ink-muted"),
        ):
            label.setStyleSheet(f"color: {c[role]}; background: transparent;")

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            self._restyle()

    def _show_screen(self) -> None:
        """Show the empty screen or the list, keeping the done screen."""
        if self._screens.currentWidget() is self._done:
            return
        self._screens.setCurrentWidget(
            self._work if self._list.has_rows() else self._empty
        )

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
        self._done.continue_btn.setText(tr("batch_continue", "Continue"))
        self._done.open_btn.setText(tr("batch_open_folder", "Open the folder"))
        self._done.undo_btn.setText(tr("batch_undo", "Undo"))
        self._update_summary()
        self._update_destination()
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
        if self._screens.currentWidget() is self._done:
            self._screens.setCurrentWidget(self._work)
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
            text = tr(
                "batch_destination",
                "To {path}. Nothing moves before you confirm.",
            ).format(path=path)
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
        self._set_progress(True, tr("searching", "Searching..."), 0)
        worker = BatchSearchWorker(
            target,
            self.media_type,
            self.content_type,
            self.parse,
            same_work=self.same_work,
            localized=self.localized,
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
        self._set_progress(False)
        self._list.apply_results(results)
        self._refresh_previews_and_action()

    def _on_search_error(self, error: str) -> None:
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
        worker = BatchSearchWorker(
            [files],
            self.media_type,
            self.content_type,
            self.parse,
            query,
            same_work=self.same_work,
            localized=self.localized,
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

    def _media_item(self, candidate: Optional[Dict[str, Any]]) -> Any:
        if not candidate:
            return None
        lang = get_config_manager().get("language", "en")
        return create_media_item(
            candidate, self.factory_type, self._manager, language=lang
        )

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

    def _row_data(self, entry: Entry) -> RowData:
        """What the row of an item shows."""
        was = entry.files[0].name
        if len(entry.files) > 1:
            was += f"  +{len(entry.files) - 1}"
        tags = self._quality_tags(entry.files[0]) if self.show_quality else []
        if entry.status == STATUS_PENDING:
            return RowData(entry.query or entry.files[0].stem, was, tags=tags)
        item = self._media_item(entry.candidate)
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
            thumbnail=self._image(url, entry.key, 72, 108),
        )

    def _quality_tags(self, file: Path) -> List[str]:
        info = FileParsingMixin.extract_quality_metadata(file.name)
        tags = [info.get("quality"), info.get("audio")]
        return [t for t in tags if t][:2]

    def _on_current_changed(self, key: Optional[Path]) -> None:
        entry = self._list.entry(key)
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
        item = self._media_item(entry.candidate)
        if item is None:
            self._scene.set_item(
                SceneItem(
                    entry.query or entry.files[0].stem,
                    entry.files[0].name,
                    shape=self.scene_shape,
                    fields=self._fields(entry, None),
                )
            )
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
        self._refresh_picker()
        self._picker.focus_search()

    def _close_picker(self) -> None:
        key = self._picking
        self._picking = None
        entry = self._list.entry(key)
        if entry is not None and entry.status == STATUS_OK:
            self._right.setCurrentWidget(self._scene_scroll)
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
            item = self._media_item(candidate)
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
        item = self._media_item(candidate)
        if item is None:
            return ""
        return self.preview_name(item, files[0])

    def _refresh_previews_and_action(self) -> None:
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

    def _update_summary(self) -> None:
        entries = self._list.entries()
        counts: Dict[str, int] = {}
        for entry in entries:
            counts[entry.status] = counts.get(entry.status, 0) + self.count_of(entry)
        total = sum(counts.values())
        self._title_lbl.setText(self._text("title", total))
        parts = []
        folder = common_folder(self._list.files())
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
        if self._action_btn.isEnabled() and self._screens.currentWidget() is self._work:
            self._start_rename()

    def _start_rename(self) -> None:
        dest = self._dest_drop.get_path()
        if not dest or not Path(dest).exists():
            message_box.warning(
                self,
                tr("warning", "Warning"),
                tr("select_dest_warning", "Please select a destination folder."),
            )
            return

        mappings: List[Tuple[Path, Any]] = []
        for files, cand in self._list.get_ready_mappings():
            item = self._media_item(cand)
            if item is None:
                continue
            mappings.extend((file, item) for file in files)

        if not mappings:
            message_box.information(self, tr("info", "Info"), self.nothing_ready_text())
            return
        if hard_link_blocked(self, [file for file, _ in mappings], str(dest)):
            return

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("confirmation", "Confirmation"))
        msg.setText(self.rename_confirm_text(len(mappings)))
        to_pick = self._list.count_by_status().get(STATUS_AMBIGUOUS, 0)
        if to_pick:
            msg.setInformativeText(
                tr(
                    "rename_skips_to_pick",
                    "{0} file(s) still to pick will be left as they are.",
                ).format(to_pick)
            )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        message_box.as_sheet(msg, self)
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        self._action_btn.setEnabled(False)
        self._set_progress(True, tr("organizing", "Organizing..."), 0)
        self._rename_started = time.monotonic()
        worker = BatchOrganizeWorker(mappings, str(dest), self.organize_method())
        self._organize_runner.run(
            worker,
            self._on_organize_done,
            self._on_organize_error,
            self._on_search_progress,
        )

    def _on_organize_done(self, report: Dict[str, Any]) -> None:
        self._set_progress(False)
        request_attention(self)
        moved = report.get("moved", [])
        left = [
            e
            for e in self._list.entries()
            if Path(e.key) not in {Path(m["from"]) for m in moved}
        ]
        # Items still to pick stay, so the user can finish them.
        self._list.remove_files([Path(m["from"]) for m in moved])
        self._files = self._list.files()
        self._update_summary()
        self._refresh_action_state()
        self._last_report = report

        success = report.get("success", 0)
        errors = report.get("errors", [])
        seconds = max(1, round(time.monotonic() - self._rename_started))
        stats = [
            StatData(
                tr("batch_stat_sorted", "Sorted"),
                str(success),
                trn("batch_seconds", seconds, "in {n} second", "in {n} seconds"),
            )
        ]
        if left:
            names = ", ".join(e.files[0].name for e in left[:2])
            stats.append(
                StatData(tr("batch_stat_left", "Left aside"), str(len(left)), names)
            )
        if errors:
            stats.append(
                StatData(
                    tr("batch_stat_errors", "Errors"), str(len(errors)), str(errors[0])
                )
            )
        if report.get("subtitles"):
            stats.append(
                StatData(
                    tr("batch_stat_subtitles", "Subtitles"), str(report["subtitles"])
                )
            )
        dest = self._dest_drop.get_path()
        changes = []
        for move in moved[:3]:
            new = Path(move.get("to", ""))
            try:
                new_text = str(new.relative_to(dest)) if dest else str(new)
            except ValueError:
                new_text = str(new)
            changes.append((Path(move["from"]).name, new_text))
        self._done.show_data(
            DoneData(
                finished=tr("batch_done_at", "Done at {0}").format(
                    datetime.now().strftime("%H:%M")
                ),
                title=self._text("done", success),
                lead=tr("batch_done_lead", "Undo puts every file back where it was."),
                stats=stats,
                changes_label=tr("batch_changes", "What changed"),
                changes=changes,
            )
        )
        self._done.undo_btn.setVisible(bool(report.get("operation")))
        self._done.history_btn.setText(
            trn(
                "batch_see_changes", len(moved), "See the change", "See the {n} changes"
            )
        )
        self._screens.setCurrentWidget(self._done)

    def _leave_done(self) -> None:
        self._screens.setCurrentWidget(self._work)
        self._show_screen()

    def _undo_last(self) -> None:
        operation = (self._last_report or {}).get("operation")
        if operation:
            undo_operation(
                self, self._organize_runner, operation, on_done=self._on_undone
            )

    def _on_undone(self, report: UndoReport) -> None:
        """Put the files back in the list, to rename them again."""
        self._last_report = None
        self._screens.setCurrentWidget(self._work)
        self.load_files([Path(move.source) for move in report.restored])
        self._show_screen()

    def _on_organize_error(self, error: str) -> None:
        self._set_progress(False)
        request_attention(self)
        self._refresh_action_state()
        message_box.critical(
            self,
            tr("error", "Error"),
            f"{tr('error_prefix', 'Error:')} {error}",
        )

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
