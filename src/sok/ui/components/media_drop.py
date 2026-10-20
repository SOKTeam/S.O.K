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
Home page drop zone and the summary of what was dropped.

The user drops files or folders of any kind; the summary lists the groups
the detector found, each opened in its page, and the files to check.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sok.core.interfaces import ContentType
from sok.file_operations.detection import (
    DetectedFile,
    DetectionReport,
    MediaGroup,
    MediaTypeDetector,
)
from sok.ui.components.base import ActionButton, Card
from sok.ui.components.inputs import DropZone, ModernComboBox
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.i18n import tr

# Kinds in the order of the type menu of a file to check.
KINDS = [
    ContentType.MOVIE,
    ContentType.EPISODE,
    ContentType.ALBUM,
    ContentType.BOOK,
    ContentType.GAME,
]


def kind_label(kind: ContentType) -> str:
    """Name of the page that organizes a kind of file."""
    return {
        ContentType.MOVIE: tr("movies", "Movies"),
        ContentType.EPISODE: tr("tv_shows", "TV Shows"),
        ContentType.ALBUM: tr("music", "Music"),
        ContentType.BOOK: tr("books", "Books"),
        ContentType.GAME: tr("games", "Games"),
    }[kind]


def reason_label(reason: str) -> str:
    """Explain to the user why a file must be checked."""
    return {
        "episode number without season": tr(
            "drop_reason_weak_episode", "Episode number without a season"
        ),
        "season folder without episode number": tr(
            "drop_reason_season_folder", "In a season folder, without an episode number"
        ),
        "video next to episodes": tr(
            "drop_reason_among_episodes", "Video among episodes: a bonus?"
        ),
        "disc image": tr(
            "drop_reason_disc_image", "Disc image: a game or a video disc?"
        ),
    }.get(reason, reason)


class MediaDropZone(DropZone):
    """Drop zone that accepts files and folders of any media type.

    Unlike DropZone it keeps no selection: each drop is sent on at once.

    Signals:
        paths_dropped (list[Path]): The dropped files and folders.
    """

    paths_dropped = Signal(list)

    def __init__(self, parent=None):
        """Initialize the drop zone.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent=parent)
        self.setMinimumHeight(110)
        self.retranslate_ui()

    def retranslate_ui(self):
        """Update the placeholder text."""
        self._placeholder = tr(
            "drop_anything_hint",
            "Drop files or folders here, or click to choose a folder",
        )
        self.update()

    def _open_dialog(self):
        """Choose a folder, the usual case (a download folder)."""
        folder = QFileDialog.getExistingDirectory(
            self, tr("select_folder_dialog", "Add a folder")
        )
        if folder:
            self.paths_dropped.emit([Path(folder)])

    def dropEvent(self, e: QDropEvent):
        """Send the dropped files and folders on.

        Args:
            e: Drop event.
        """
        self._hover = False
        self.update()
        paths = [Path(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile()]
        paths = [p for p in paths if p.exists()]
        if paths:
            e.acceptProposedAction()
            self.paths_dropped.emit(paths)


class _GroupRow(QWidget):
    """One group of the summary: title, count, state and an Open button."""

    open_clicked = Signal()

    def __init__(self, group: MediaGroup, remaining: int, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        if group.kind == ContentType.MOVIE:
            title = kind_label(group.kind)
        else:
            title = group.title or tr("drop_untitled", "Untitled")
        title_lbl = QLabel(title)
        title_lbl.setObjectName("RowTitle")
        title_lbl.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        texts.addWidget(title_lbl)

        total = len(group.files)
        detail = tr("drop_files_count", "{count} file(s)").format(count=total)
        if group.kind != ContentType.MOVIE:
            detail = f"{kind_label(group.kind)} · {detail}"
        detail_lbl = QLabel(detail)
        detail_lbl.setObjectName("EmptyState")
        texts.addWidget(detail_lbl)
        layout.addLayout(texts, 1)

        if remaining == 0:
            state = tr("drop_done", "✓ Organized")
        elif remaining < total:
            state = tr("drop_remaining", "{count} of {total} left").format(
                count=remaining, total=total
            )
        else:
            state = ""
        if state:
            state_lbl = QLabel(state)
            state_lbl.setObjectName("EmptyState")
            layout.addWidget(state_lbl)

        if remaining:
            btn = ActionButton(tr("drop_open", "Open"))
            btn.clicked.connect(self.open_clicked.emit)
            layout.addWidget(btn)


class _CheckRow(QWidget):
    """A file to check: name, reason, a type menu and an Add button."""

    confirmed = Signal(object)

    def __init__(self, item: DetectedFile, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        name_lbl = QLabel(item.path.name)
        name_lbl.setObjectName("RowTitle")
        name_lbl.setToolTip(str(item.path))
        name_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        texts.addWidget(name_lbl)
        reason_lbl = QLabel(reason_label(item.reason))
        reason_lbl.setObjectName("EmptyState")
        texts.addWidget(reason_lbl)
        layout.addLayout(texts, 1)

        self._combo = ModernComboBox()
        for kind in KINDS:
            self._combo.addItem(kind_label(kind), kind)
        self._combo.setCurrentIndex(KINDS.index(item.kind))
        layout.addWidget(self._combo)

        btn = ActionButton(tr("drop_add", "Add"))
        btn.clicked.connect(lambda: self.confirmed.emit(self._combo.currentData()))
        layout.addWidget(btn)


class DropSummary(QWidget):
    """Summary of the last drop on the home page.

    Signals:
        open_requested (MediaGroup, list[Path]): Open a group in its page,
            with the files of the group that are still in place.
    """

    open_requested = Signal(object, list)

    def __init__(self, detector: MediaTypeDetector, parent=None):
        """Initialize the summary, hidden until a drop is analyzed.

        Args:
            detector: Detector that confirms the files to check.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._detector = detector
        self._report: Optional[DetectionReport] = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self.setVisible(False)

    def set_report(self, report: Optional[DetectionReport]):
        """Show a new report, or hide the summary with None.

        Args:
            report: Result of the detection.
        """
        self._report = report
        self.refresh()

    def show_message(self, text: str):
        """Replace the summary with a message, such as "Analyzing…".

        Args:
            text: Message to show.
        """
        self._report = None
        self._clear()
        lbl = QLabel(text)
        lbl.setObjectName("EmptyState")
        lbl.setWordWrap(True)
        self._layout.addWidget(lbl)
        self.setVisible(True)

    def refresh(self):
        """Rebuild the rows, with the state of each group.

        A file that is no longer where it was dropped has been organized.
        """
        self._clear()
        report = self._report
        if report is None:
            self.setVisible(False)
            return
        self.setVisible(True)

        header = QHBoxLayout()
        title = make_section_label("drop_last_count", "Last drop: {count} file(s)")
        title.setText(
            tr("drop_last_count", "Last drop: {count} file(s)").format(
                count=report.total_files
            )
        )
        header.addWidget(title)
        header.addStretch()
        clear_btn = QPushButton(tr("drop_clear", "Clear"))
        clear_btn.setObjectName("SmallBtn")
        clear_btn.setFixedHeight(24)
        clear_btn.setStyleSheet("padding: 0 10px;")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(lambda: self.set_report(None))
        header.addWidget(clear_btn)
        self._layout.addLayout(header)

        if report.total_files == 0:
            lbl = QLabel(
                tr(
                    "drop_nothing_found",
                    "No media file recognized. Accepted files: {extensions}."
                    " Archives, programs and text documents are only accepted"
                    " in the page of their type.",
                ).format(extensions=", ".join(self._detector.supported_extensions))
            )
            lbl.setObjectName("EmptyState")
            lbl.setWordWrap(True)
            self._layout.addWidget(lbl)
            return

        if report.groups:
            card = Card()
            for group in report.groups:
                remaining = [f for f in group.files if f.exists()]
                row = _GroupRow(group, len(remaining))
                row.open_clicked.connect(
                    lambda g=group: self._open(g)  # type: ignore[misc]
                )
                card.add(row)
            self._layout.addWidget(card)

        if report.to_check:
            check_lbl = make_section_label("drop_to_check", "To check")
            check_lbl.setText(tr("drop_to_check", "To check"))
            self._layout.addWidget(check_lbl)
            card = Card()
            for item in report.to_check:
                row = _CheckRow(item)
                row.confirmed.connect(
                    lambda kind, i=item: self._confirm(i, kind)  # type: ignore[misc]
                )
                card.add(row)
            self._layout.addWidget(card)

    def _open(self, group: MediaGroup):
        """Ask for a group to be opened with its files still in place."""
        files: List[Path] = [f for f in group.files if f.exists()]
        if files:
            self.open_requested.emit(group, files)

    def _confirm(self, item: DetectedFile, kind: ContentType):
        """Move a file to check into a group with the chosen type."""
        if self._report is None:
            return
        self._detector.confirm(self._report, item, kind)
        self.refresh()

    def _clear(self):
        """Remove every row."""
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget() is not None:
                _delete_widget(child.widget())
            elif child.layout() is not None:
                _delete_layout(child.layout())


def _delete_widget(widget):
    """Remove a widget from the summary at once, and delete it later."""
    widget.setParent(None)
    widget.deleteLater()


def _delete_layout(layout):
    """Delete the widgets of a nested layout."""
    while layout.count():
        child = layout.takeAt(0)
        if child.widget() is not None:
            _delete_widget(child.widget())
        elif child.layout() is not None:
            _delete_layout(child.layout())
