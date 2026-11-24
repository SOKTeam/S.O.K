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
"""
Home page: what there is to sort, by media type, and the disks.

The first screen of the app. Files dropped anywhere on it are sorted by
type and sent to their page; a row per media type then says what that page
has to sort, with a key to open it. Files whose type is a guess wait in a
list to check. A band recalls the last rename, with Undo; the scene at the
right shows the covers waiting and the room left on the disks.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from PySide6.QtCore import QObject, QPointF, QRectF, QStorageInfo, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
    QShortcut,
)
from PySide6.QtWidgets import (
    QBoxLayout,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QVBoxLayout,
    QWidget,
)

from sok.config import get_config_manager
from sok.core.history import get_history
from sok.core.interfaces import ContentType
from sok.file_operations.detection import (
    DetectedFile,
    DetectionReport,
    MediaTypeDetector,
)
from sok.ui.components.base import KeyButton, parse_color
from sok.ui.components.media_drop import CheckRow
from sok.ui.components.media_visual import (
    draw_fan,
    dominant_color,
    standin_colors,
)
from sok.ui.controllers.undo import undo_operation
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.i18n import tr, trn
from sok.ui.pages.batch_page import (
    PageSummary,
    display_path,
    human_size,
    shortcut_label,
)
from sok.ui.responsive import fit_display, side_width
from sok.ui.theme import Theme, ui_font
from sok.ui.tokens import RADIUS
from sok.ui.workers import DetectionWorker

logger = logging.getLogger(__name__)


def mac_volumes() -> dict[str, str]:
    """Return the macOS startup disk and mounted volumes.

    Returns:
        Volume names (such as "Macintosh HD") by root path.
    """
    volumes = {}
    for volume in QStorageInfo.mountedVolumes():
        root = volume.rootPath()
        if not (volume.isValid() and volume.isReady()):
            continue
        if root == "/" or root.startswith("/Volumes/"):
            volumes[root] = volume.displayName() or Path(root).name
    return volumes


# Where Linux mounts other disks: udisks (removable and internal drives
# opened from the file manager) and manual mounts.
LINUX_MOUNT_DIRS = ("/media/", "/run/media/", "/mnt/")


def linux_volumes() -> dict[str, str]:
    """Return the Linux system disk, a separate /home and mounted disks.

    Pseudo file systems (/proc, /run, snaps, the AppImage mount...) live
    outside these folders, so they are left out.

    Returns:
        Volume names (the file system label, else the folder name) by root
        path.
    """
    volumes = {}
    for volume in QStorageInfo.mountedVolumes():
        root = volume.rootPath()
        if not (volume.isValid() and volume.isReady()):
            continue
        if root == "/":
            volumes[root] = volume.name() or tr("system_drive", "System")
        elif root == "/home" or root.startswith(LINUX_MOUNT_DIRS):
            volumes[root] = volume.name() or Path(root).name
    return volumes


def first_name() -> str:
    """First name of the account of the computer, or "" when unknown."""
    try:
        if sys.platform == "win32":
            import ctypes

            size = ctypes.c_ulong(0)
            ctypes.windll.secur32.GetUserNameExW(3, None, ctypes.byref(size))
            buffer = ctypes.create_unicode_buffer(size.value)
            if ctypes.windll.secur32.GetUserNameExW(3, buffer, ctypes.byref(size)):
                name = buffer.value
            else:
                return ""
        else:
            import pwd

            name = pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0]
    except (OSError, KeyError, AttributeError, ImportError):
        return ""
    parts = name.split()
    return parts[0] if parts else ""


def when_text(moment: datetime, today: Optional[date] = None) -> str:
    """ "today at 21:42", "yesterday at 21:42" or "on 12/11 at 21:42"."""
    today = today or date.today()
    clock = moment.strftime("%H:%M")
    days = (today - moment.date()).days
    if days == 0:
        return tr("home_today_at", "today at {0}").format(clock)
    if days == 1:
        return tr("home_yesterday_at", "yesterday at {0}").format(clock)
    return tr("home_on_at", "on {0} at {1}").format(moment.strftime("%d/%m"), clock)


@dataclass
class Disk:
    """A disk the files go to: its name, size and free room."""

    label: str
    total: int
    free: int

    @property
    def used(self) -> int:
        return self.total - self.free


def _volume_of(path: Path) -> Tuple[str, str]:
    """Root and name of the volume holding a path."""
    info = QStorageInfo(str(path))
    root = info.rootPath() if info.isValid() else path.anchor
    name = info.displayName() if info.isValid() else ""
    if root == "/" and sys.platform == "darwin":
        name = mac_volumes().get("/", name)
    return root, name or Path(root).name or root


class DiskWorker(QObject):
    """Reads the size and free room of the disks of some folders.

    Signals:
        finished(list): The disks, one per volume.
        error(str): Message of an unexpected failure.
    """

    finished = Signal(list)
    error = Signal(str)

    def __init__(self, folders: Sequence[Path]):
        super().__init__()
        self._folders = list(folders)

    def stop(self) -> None:
        """Nothing to stop: reading a disk is quick."""

    def run(self) -> None:
        disks: List[Disk] = []
        seen: set[str] = set()
        for folder in self._folders:
            try:
                root, name = _volume_of(folder)
                if root in seen:
                    continue
                total, _used, free = shutil.disk_usage(root)
            except OSError as exc:
                logger.debug("Disk read failed for %s: %s", folder, exc)
                continue
            seen.add(root)
            disks.append(Disk(name, total, free))
        self.finished.emit(disks)


def destination_folders() -> List[Path]:
    """The default folders of the settings that exist, else the home folder."""
    config = get_config_manager()
    folders = []
    for key in (
        "default_video_path",
        "default_series_path",
        "default_music_path",
        "default_books_path",
        "default_games_path",
    ):
        value = config.get(key, "")
        if value and Path(value).is_dir():
            folders.append(Path(value))
    return folders or [Path.home()]


def _palette(widget: QWidget) -> dict[str, str]:
    return getattr(widget.window(), "c", None) or Theme.DARK


class TypeRow(QWidget):
    """A media type on the home page: covers, name, counts, size, "See".

    Signals:
        open_clicked: Open the page of the type.
    """

    open_clicked = Signal()
    HEIGHT = 84

    def __init__(self, square: bool = False):
        super().__init__()
        self._square = square
        self._name = ""
        self._summary = PageSummary()
        self._hovered = False
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 14, 0)
        layout.addStretch()
        self.open_btn = KeyButton("", small=True)
        self.open_btn.clicked.connect(self.open_clicked.emit)
        layout.addWidget(self.open_btn)

    def set_summary(self, name: str, summary: PageSummary) -> None:
        self.open_btn.setText(tr("home_see", "See"))
        self._name = name
        self._summary = summary
        self.open_btn.setVisible(summary.total > 0)
        self.update()

    def enterEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = True
        self.update()

    def leaveEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = False
        self.update()

    def mouseReleaseEvent(self, e):  # noqa: N802 - Qt API
        if e.button() == Qt.MouseButton.LeftButton and self._summary.total:
            self.open_clicked.emit()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        s = self._summary
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hovered and s.total:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(parse_color(c["surface-raised"]))
            p.drawRoundedRect(QRectF(self.rect()), 14, 14)
        size = (40, 40) if self._square else (34, 51)
        covers = s.covers or []
        if covers:
            draw_fan(
                p,
                covers[:3],
                14,
                (self.HEIGHT - size[1]) / 2,
                size,
                14,
                6,
                self.devicePixelRatioF(),
            )
        left = 14 + 62 + 18
        name_font = ui_font(22, 600)
        name_font.setLetterSpacing(name_font.SpacingType.AbsoluteSpacing, -0.66)
        p.setFont(name_font)
        p.setPen(parse_color(c["ink"] if s.total else c["ink-faint"]))
        p.drawText(left, int(self.HEIGHT / 2 - 2), self._name)

        line_font = ui_font(14)
        p.setFont(line_font)
        y = int(self.HEIGHT / 2 + 20)
        if not s.total:
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(left, y, tr("home_nothing", "Nothing to sort for now"))
        else:
            recognized = trn(
                "home_recognized", s.ready, "{n} recognized", "{n} recognized"
            )
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(left, y, recognized)
            if s.waiting:
                x = left + QFontMetrics(line_font).horizontalAdvance(recognized + " · ")
                p.drawText(
                    left + QFontMetrics(line_font).horizontalAdvance(recognized),
                    y,
                    " · ",
                )
                p.setPen(parse_color(c["caution"]))
                p.drawText(
                    x,
                    y,
                    trn("home_to_check", s.waiting, "{n} to check", "{n} to check"),
                )
            size_text = human_size(s.size) if s.size else ""
            mono = ui_font(13, 400, mono=True, tabular=True)
            p.setFont(mono)
            p.setPen(parse_color(c["ink-faint"]))
            right = self.open_btn.x() - 18
            width = QFontMetrics(mono).horizontalAdvance(size_text)
            p.drawText(int(right - width), int(self.HEIGHT / 2 + 5), size_text)
        p.end()


class HomeScene(QWidget):
    """The right of the home page: covers waiting, and the disks."""

    # The covers or the size moved: the window repaints the light.
    light_changed = Signal()

    def __init__(self):
        super().__init__()
        self.inline_light = True
        self.setMinimumWidth(360)
        self._covers: List[Tuple[Optional[QPixmap], str]] = []
        self._disks: List[Disk] = []
        self._room = ""
        self._color = QColor(128, 128, 128)

    def set_covers(self, covers: List[Tuple[Optional[QPixmap], str]]) -> None:
        self._covers = covers[:4]
        if covers:
            pixmap, title = covers[0]
            self._color = dominant_color(pixmap) if pixmap else standin_colors(title)[0]
        self.update()
        self.light_changed.emit()

    def paint_light_into(self, p: QPainter, offset: QPointF, area: QRectF) -> None:
        """The ambient light of the covers, painted in a widget where this
        one is at offset."""
        if not self._covers:
            return
        center = offset + QPointF(self.width() / 2, self.height() * 0.22)
        light = QRadialGradient(center, 420)
        tint = QColor(self._color)
        tint.setAlphaF(0.12)
        light.setColorAt(0, tint)
        tint.setAlphaF(0)
        light.setColorAt(1, tint)
        p.fillRect(area, light)

    def resizeEvent(self, e):  # noqa: N802 - Qt API
        super().resizeEvent(e)
        self.light_changed.emit()

    def set_disks(self, disks: List[Disk], room: str = "") -> None:
        self._disks = disks[:2]
        self._room = room
        self.update()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        # The window paints the background and the light (see LightColumn).
        p.setPen(QPen(parse_color(c["line"]), 1))
        p.drawLine(QPointF(0.5, 0), QPointF(0.5, rect.height()))

        pad = 44
        y = 60.0
        if self._covers:
            w, h = 150, 225
            step = 56
            span = w + step * (len(self._covers) - 1)
            x = (rect.width() - span) / 2
            draw_fan(
                p,
                self._covers,
                x,
                y,
                (w, h),
                step,
                RADIUS["poster"],
                self.devicePixelRatioF(),
            )
            floor = QRadialGradient(QPointF(rect.width() / 2, y + h + 14), span / 2)
            floor.setColorAt(0, QColor(0, 0, 0, 200))
            floor.setColorAt(1, QColor(0, 0, 0, 0))
            p.save()
            p.translate(rect.width() / 2, y + h + 14)
            p.scale(1, 20 / span)
            p.translate(-rect.width() / 2, -(y + h + 14))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(floor)
            p.drawEllipse(QPointF(rect.width() / 2, y + h + 14), span / 2, span / 2)
            p.restore()
            y += h + 70

        if not self._disks:
            p.end()
            return
        label = ui_font(11, 600)
        label.setLetterSpacing(label.SpacingType.AbsoluteSpacing, 0.88)
        label.setCapitalization(label.Capitalization.AllUppercase)
        p.setFont(label)
        p.setPen(parse_color(c["ink-faint"]))
        p.drawText(
            QRectF(pad, y, rect.width() - 2 * pad, 16),
            Qt.AlignmentFlag.AlignCenter,
            tr("home_disks", "Your disks"),
        )
        y += 34
        width = rect.width() - 2 * pad
        for disk in self._disks:
            amount = tr("home_used_of", "{0} of {1}").format(
                human_size(disk.used), human_size(disk.total)
            )
            mono = ui_font(13, 400, mono=True, tabular=True)
            # The name gets what the amount leaves, shortened if need be.
            name_room = width - 14 - QFontMetrics(mono).horizontalAdvance(amount) - 12
            name = QFontMetrics(ui_font(13)).elidedText(
                disk.label, Qt.TextElideMode.ElideRight, max(0, int(name_room))
            )
            p.setFont(ui_font(13))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(parse_color(c["ink"]))
            p.drawEllipse(QPointF(pad + 3, y + 8), 3, 3)
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(
                QRectF(pad + 14, y, width - 14, 18),
                Qt.AlignmentFlag.AlignVCenter,
                name,
            )
            p.setFont(mono)
            p.setPen(parse_color(c["ink"]))
            p.drawText(
                QRectF(pad, y, width, 18),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                amount,
            )
            y += 28
            bar = QRectF(pad, y, width, 4)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(parse_color(c["line-strong"]))
            p.drawRoundedRect(bar, 2, 2)
            share = disk.used / disk.total if disk.total else 0
            p.setBrush(parse_color(c["ink"]))
            p.drawRoundedRect(QRectF(pad, y, width * share, 4), 2, 2)
            y += 18
            p.setFont(ui_font(13))
            p.setPen(parse_color(c["ink-faint"]))
            free = tr("home_free", "{0} free.").format(human_size(disk.free))
            p.drawText(QRectF(pad, y, width, 18), Qt.AlignmentFlag.AlignVCenter, free)
            y += 34
        if self._room:
            p.setFont(ui_font(13))
            p.setPen(parse_color(c["ink-faint"]))
            p.drawText(
                QRectF(pad, y - 10, width, 40),
                Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                self._room,
            )
        p.end()


class HomePage(QWidget):
    """The first screen: what there is to sort, by media type.

    Signals:
        navigate(int): Open the page of this index.
        open_group(MediaGroup, list): Send files of a dropped group to the
            page of their type.
    """

    navigate = Signal(int)
    open_group = Signal(object, list)
    # The light of the page moved: the window paints it again.
    light_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Page")
        self._detector = MediaTypeDetector()
        self._detection_runner = WorkerRunner(self)
        self._disk_runner = WorkerRunner(self)
        self._undo_runner = WorkerRunner(self)
        # (page index, name, page, square covers) of each media type.
        self._pages: List[Tuple[int, Callable[[], str], object, bool]] = []
        self._report: Optional[DetectionReport] = None
        self._analyzing = False
        self._nothing_found = False
        self._disks: List[Disk] = []
        self._build()
        self.setAcceptDrops(True)

    # ---------------------------------------------------------------- UI

    def _build(self) -> None:
        columns = QHBoxLayout(self)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")
        content = QWidget()
        content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        left = QVBoxLayout(content)
        left.setContentsMargins(26, 40, 26, 24)
        left.setSpacing(0)
        scroll.setWidget(content)

        head = QVBoxLayout()
        head.setContentsMargins(14, 0, 14, 0)
        head.setSpacing(10)
        self._hello = QLabel()
        hello = ui_font(11, 600)
        hello.setLetterSpacing(hello.SpacingType.AbsoluteSpacing, 0.88)
        hello.setCapitalization(hello.Capitalization.AllUppercase)
        self._hello.setFont(hello)
        head.addWidget(self._hello)
        self._title = QLabel()
        title = ui_font(52, 650)
        title.setLetterSpacing(title.SpacingType.AbsoluteSpacing, -2.08)
        self._title.setFont(title)
        self._title.setWordWrap(True)
        head.addWidget(self._title)
        self._lead = QLabel()
        self._lead.setFont(ui_font(17))
        self._lead.setWordWrap(True)
        head.addWidget(self._lead)
        left.addLayout(head)
        left.addSpacing(28)

        self._rows_box = QVBoxLayout()
        self._rows_box.setSpacing(2)
        left.addLayout(self._rows_box)
        self._rows: List[TypeRow] = []

        self._check_label = QLabel()
        self._check_label.setFont(hello)
        self._check_label.setContentsMargins(14, 24, 14, 8)
        self._check_label.setVisible(False)
        left.addWidget(self._check_label)
        self._checks = QVBoxLayout()
        self._checks.setSpacing(2)
        left.addLayout(self._checks)

        self._band = QFrame()
        self._band.setObjectName("HomeBand")
        band = QHBoxLayout(self._band)
        band.setContentsMargins(18, 12, 12, 12)
        band.setSpacing(16)
        self._band_text = QLabel()
        self._band_text.setFont(ui_font(14))
        self._band_text.setWordWrap(True)
        self._band_text.setTextFormat(Qt.TextFormat.RichText)
        band.addWidget(self._band_text, 1)
        self._undo_btn = KeyButton("", small=True)
        self._undo_btn.clicked.connect(self._undo_last)
        band.addWidget(self._undo_btn)
        left.addSpacing(20)
        left.addWidget(self._band)
        left.addStretch()

        # The action stays at the bottom, out of the scrolled part.
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 24)
        column.setSpacing(0)
        column.addWidget(scroll, 1)
        # Side by side, or the note under the key in a narrow window.
        actions = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._actions = actions
        actions.setContentsMargins(40, 16, 40, 0)
        actions.setSpacing(12)
        self._choose_btn = KeyButton("", primary=True)
        self._choose_btn.set_shortcut(shortcut_label("O"))
        self._choose_btn.clicked.connect(self._browse)
        actions.addWidget(self._choose_btn)
        self._note = QLabel()
        self._note.setFont(ui_font(13))
        self._note.setWordWrap(True)
        actions.addWidget(self._note, 1)
        column.addLayout(actions)
        columns.addLayout(column, 1)

        self._scene = HomeScene()
        self._scene.setFixedWidth(side_width(1440))
        self._scene.inline_light = True
        self._scene.light_changed.connect(self.light_changed.emit)
        columns.addWidget(self._scene)

        shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        shortcut.activated.connect(self._browse)
        self.retranslateUi()

    def set_pages(
        self, pages: List[Tuple[int, Callable[[], str], object, bool]]
    ) -> None:
        """The media pages, in the order of the navigation: (index, name,
        page, square covers)."""
        self._pages = pages
        for row in self._rows:
            row.deleteLater()
        self._rows = []
        for index, _name, _page, square in pages:
            row = TypeRow(square)
            row.open_clicked.connect(lambda i=index: self.navigate.emit(i))
            self._rows_box.addWidget(row)
            self._rows.append(row)
        self.update_summary()

    def _restyle(self) -> None:
        c = _palette(self)
        for label, role in (
            (self._hello, "ink-faint"),
            (self._title, "ink"),
            (self._lead, "ink-muted"),
            (self._check_label, "ink-faint"),
            (self._note, "ink-muted"),
            (self._band_text, "ink-muted"),
        ):
            label.setStyleSheet(f"color: {c[role]}; background: transparent;")
        self._band.setStyleSheet(
            f"#HomeBand {{ background: {c['surface']}; border: 1px solid {c['line']};"
            f" border-radius: 14px; }}"
        )
        # Its sentence holds colors of the theme.
        self._update_band()

    def resizeEvent(self, e):  # noqa: N802 - Qt API
        """The scene, the title and the key follow the size of the page."""
        super().resizeEvent(e)
        self._scene.setFixedWidth(side_width(self.width()))
        fit_display([self._title], self.width())
        narrow = self.width() - side_width(self.width()) < 560
        self._actions.setDirection(
            QBoxLayout.Direction.TopToBottom
            if narrow
            else QBoxLayout.Direction.LeftToRight
        )
        self._actions.setAlignment(
            self._choose_btn,
            Qt.AlignmentFlag.AlignLeft if narrow else Qt.AlignmentFlag(0),
        )

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            self._restyle()

    def light_source(self):
        """The widget whose light the window paints, or None (see
        main_window.LightColumn)."""
        return self._scene

    def retranslateUi(self) -> None:
        self._choose_btn.setText(tr("batch_choose_folder", "Choose a folder"))
        self._undo_btn.setText(tr("home_undo_last", "Undo this rename"))
        self._check_label.setText(tr("drop_to_check", "To check"))
        self._note.setText(
            tr("home_note", "You can also drop files anywhere on the window.")
        )
        self.update_summary()

    # ------------------------------------------------------------ Content

    def refresh(self) -> None:
        """Read the pages, the last rename and the disks again."""
        self.update_summary()
        self._update_band()
        self._disk_runner.run(
            DiskWorker(destination_folders()), self._on_disks, lambda _e: None
        )

    def update_summary(self) -> None:
        """Sentence, rows and scene from what the pages have to sort."""
        total = ready = waiting = 0
        covers: List[Tuple[Optional[QPixmap], str]] = []
        movie_sizes: List[int] = []
        summaries = []
        for row, (index, name, page, _square) in zip(self._rows, self._pages):
            summary: PageSummary = page.summary()  # type: ignore[attr-defined]
            row.set_summary(name(), summary)
            summaries.append(summary)
            total += summary.total
            ready += summary.ready
            waiting += summary.waiting
            if summary.covers:
                covers.append(summary.covers[0])
            if index == 2 and summary.total:
                movie_sizes.append(summary.size // summary.total)
        # Nothing to sort: the screen is a sentence and an action.
        for row in self._rows:
            row.setVisible(bool(total))
        self._hello.setText(self._hello_text())
        if self._analyzing:
            self._title.setText(tr("home_sorting", "Sorting the files…"))
            self._lead.setText("")
        elif total:
            self._title.setText(
                trn("home_title", total, "{n} item to sort.", "{n} items to sort.")
            )
            parts = []
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
            self._lead.setText(" ".join(parts))
        else:
            self._title.setText(tr("home_empty_title", "Drop everything here."))
            self._lead.setText(
                tr(
                    "home_empty_text",
                    "Movies, TV shows, music, books, games: S.O.K recognizes each "
                    "file and sends it to the right screen.",
                )
            )
        if self._nothing_found:
            self._lead.setText(
                tr(
                    "drop_nothing_found",
                    "No media file recognized. Accepted files: {extensions}.",
                ).format(extensions=", ".join(self._detector.supported_extensions))
            )
        self._scene.set_covers(covers)
        room = ""
        if movie_sizes and self._disks:
            average = sum(movie_sizes) / len(movie_sizes)
            if average:
                count = int(self._disks[0].free / average)
                room = trn(
                    "home_room_movies",
                    count,
                    "Room left for about {n} movie of this size.",
                    "Room left for about {n} movies of this size.",
                )
        self._scene.set_disks(self._disks, room)
        self._restyle()

    def _hello_text(self) -> str:
        name = first_name()
        hello = (
            tr("home_hello_name", "Hello {0}").format(name)
            if name
            else tr("home_hello", "Hello")
        )
        operations = [op for op in get_history().operations() if op.moves]
        if not operations:
            return hello
        try:
            moment = datetime.fromisoformat(operations[0].date)
        except ValueError:
            return hello
        last = tr("home_last_rename", "last rename {0}").format(when_text(moment))
        return f"{hello} · {last}"

    def _update_band(self) -> None:
        operations = [op for op in get_history().operations() if op.moves]
        op = operations[0] if operations else None
        if op is None or op.undone:
            self._band.setVisible(False)
            return
        try:
            moment = datetime.fromisoformat(op.date)
        except ValueError:
            self._band.setVisible(False)
            return
        c = _palette(self)
        moved = [m for m in op.moves if not m.follows]
        targets = [Path(m.target).parent for m in moved] or [
            Path(op.moves[0].target).parent
        ]
        try:
            folder = Path(os.path.commonpath([str(t) for t in targets]))
        except ValueError:
            folder = targets[0]
        when = when_text(moment)
        sentence = trn(
            "home_band",
            len(moved),
            "{when}, {n} file sorted",
            "{when}, {n} files sorted",
        ).replace("{when}", when[:1].upper() + when[1:])
        path = (
            f"<span style='font-family: \"{Theme.MONO}\"'>{display_path(folder)}</span>"
        )
        to = tr("home_band_to", "to {path}.").format(path=path)
        self._band_text.setText(
            f"<span style='color: {c['ink']}'>{sentence}</span> {to}"
        )
        self._band.setVisible(True)
        self._last_operation = op.id

    def _undo_last(self) -> None:
        op_id = getattr(self, "_last_operation", None)
        if op_id:
            undo_operation(
                self, self._undo_runner, op_id, on_done=lambda _r: self.refresh()
            )

    def _on_disks(self, disks: List[Disk]) -> None:
        self._disks = disks
        self.update_summary()

    # -------------------------------------------------------------- Drops

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, tr("select_folder_dialog", "Add folder")
        )
        if folder:
            self._analyze([Path(folder)])

    def dragEnterEvent(self, event):  # noqa: N802 - Qt API
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802 - Qt API
        self._analyze([Path(u.toLocalFile()) for u in event.mimeData().urls()])
        event.acceptProposedAction()

    def _analyze(self, paths: List[Path]) -> None:
        self._analyzing = True
        self._nothing_found = False
        self.update_summary()
        worker = DetectionWorker(paths, self._detector)
        self._detection_runner.run(worker, self._on_analyzed, self._on_analyze_error)

    def _on_analyzed(self, report: DetectionReport) -> None:
        """Send each group to its page; keep the files to check here."""
        self._analyzing = False
        self._nothing_found = report.total_files == 0
        for group in report.groups:
            self.open_group.emit(group, list(group.files))
        self._report = report
        self._show_checks()
        self.update_summary()

    def _on_analyze_error(self, error: str) -> None:
        self._analyzing = False
        self.update_summary()
        self._lead.setText(
            tr("drop_error", "The files could not be analyzed: {error}").format(
                error=error
            )
        )

    def _show_checks(self) -> None:
        while self._checks.count():
            item = self._checks.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                widget.deleteLater()
        to_check = self._report.to_check if self._report else []
        self._check_label.setVisible(bool(to_check))
        for detected in to_check:
            row = CheckRow(detected)
            row.confirmed.connect(lambda kind, d=detected: self._confirm(d, kind))
            self._checks.addWidget(row)

    def _confirm(self, detected: DetectedFile, kind: ContentType) -> None:
        """Send a file to check to the page of the chosen type."""
        if self._report is None:
            return
        self._detector.confirm(self._report, detected, kind)
        group = next((g for g in self._report.groups if detected.path in g.files), None)
        if group is not None:
            self.open_group.emit(group, [detected.path])
        self._show_checks()
        self.update_summary()

    def stop_workers(self) -> None:
        self._detection_runner.stop()
        self._disk_runner.stop()
        self._undo_runner.stop()

    def closeEvent(self, event):  # noqa: N802 - Qt API
        self.stop_workers()
        super().closeEvent(event)
