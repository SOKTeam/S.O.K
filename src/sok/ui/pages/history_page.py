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
"""History page: the renames done, and a way to undo them.

Each rename is a card: what was renamed, when, and an Undo button. A click
on the card shows its files, each of which can be put back on its own.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QDateTime, QLocale, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sok.config.config_manager import get_config_manager
from sok.core.history import Operation, get_history
from sok.ui import message_box
from sok.ui.components.base import ActionButton, Card
from sok.ui.controllers.undo import undo_operation
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.i18n import tr
from sok.ui.theme import card_shadow, set_tone

# Label of the page an operation was made on, by its kind.
KIND_LABELS = {
    "movie": ("movies", "Movies"),
    "tv_series": ("tv_shows", "TV Shows"),
    "episode": ("tv_shows", "TV Shows"),
    "album": ("music", "Music"),
    "track": ("music", "Music"),
    "book": ("books", "Books"),
    "game": ("games", "Games"),
}


def operation_title(operation: Operation) -> str:
    """ "Movies · 12 file(s)", and " · 5 subtitle(s)" when some followed."""
    key, default = KIND_LABELS.get(operation.kind, ("files", "Files"))
    followers = sum(move.follows is not None for move in operation.moves)
    count = tr("history_files", "{0} file(s)").format(len(operation.moves) - followers)
    title = f"{tr(key, default)} · {count}"
    if followers:
        title += " · " + tr("history_subtitles", "{0} subtitle(s)").format(followers)
    return title


def operation_date(operation: Operation) -> str:
    """The date of an operation, written the way of the interface language."""
    date = QDateTime.fromString(operation.date, Qt.DateFormat.ISODate)
    if not date.isValid():
        return operation.date
    locale = QLocale(get_config_manager().get("language", "en"))
    return locale.toString(date, QLocale.FormatType.ShortFormat)


class OperationCard(Card):
    """One rename: a header with its Undo button, and its files when open."""

    def __init__(self, operation: Operation, page: "HistoryPage"):
        super().__init__()
        self._operation = operation
        self._page = page
        self._files: Optional[QWidget] = None
        self._open = False

        header = QWidget()
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.mousePressEvent = lambda _event: self._toggle()  # type: ignore[method-assign]
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        title = QLabel(operation_title(operation))
        title.setObjectName("RowTitle")
        status = operation_date(operation)
        if operation.undone:
            status += " · " + tr("history_undone", "Undone")
        elif operation.partly_undone:
            status += " · " + tr("history_partly_undone", "Partly undone")
        subtitle = QLabel(status)
        subtitle.setObjectName("RowSubtitle")
        texts.addWidget(title)
        texts.addWidget(subtitle)
        layout.addLayout(texts, 1)

        if not operation.undone:
            undo = ActionButton(tr("undo", "Undo"))
            undo.clicked.connect(self._undo_all)
            layout.addWidget(undo)
        self._chevron = QLabel("›")
        self._chevron.setObjectName("RowSubtitle")
        self._chevron.setFixedWidth(16)
        layout.addWidget(self._chevron)

        self.add(header)
        self.setGraphicsEffect(card_shadow())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _toggle(self) -> None:
        """Show or hide the files of the operation."""
        self._open = not self._open
        if self._files is None:
            self._files = self._build_files()
            self.add(self._files)
        self._files.setVisible(self._open)
        self._chevron.setText("⌄" if self._open else "›")

    def _build_files(self) -> QWidget:
        files = QWidget()
        layout = QVBoxLayout(files)
        layout.setContentsMargins(12, 4, 12, 8)
        layout.setSpacing(2)
        for index, move in enumerate(self._operation.moves):
            line = QHBoxLayout()
            if move.follows:
                # A subtitle, under its video.
                line.addSpacing(20)
            label = QLabel(f"{Path(move.source).name}  →  {Path(move.target).name}")
            label.setToolTip(f"{move.source}\n→ {move.target}")
            label.setObjectName("RowSubtitle")
            line.addWidget(label, 1)
            if move.undone:
                done = QLabel(tr("history_undone", "Undone"))
                done.setObjectName("RowSubtitle")
                set_tone(label, "disabled")
                set_tone(done, "disabled")
                line.addWidget(done)
            else:
                button = QPushButton("↺")
                button.setObjectName("PatternRemoveBtn")
                button.setFixedSize(20, 20)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setToolTip(tr("history_undo_file", "Put this file back"))
                button.clicked.connect(lambda _=False, i=index: self._undo_file(i))
                line.addWidget(button)
            layout.addLayout(line)
        return files

    def _undo_all(self) -> None:
        count = sum(not move.undone for move in self._operation.moves)
        answer = message_box.question(
            self,
            tr("undo", "Undo"),
            tr("history_confirm_undo", "Put {0} file(s) back where they were?").format(
                count
            ),
        )
        if answer == message_box.StandardButton.Yes:
            self._page.undo(self._operation.id)

    def _undo_file(self, index: int) -> None:
        self._page.undo(self._operation.id, index)


class HistoryPage(QScrollArea):
    """Page listing the renames of the history, newest first."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("Page")
        self._runner = WorkerRunner(self)
        self._cards: List[OperationCard] = []
        self._build()
        self.retranslateUi()
        self.refresh()

    def _build(self) -> None:
        content = QWidget()
        content.setObjectName("PageContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        self._clear_btn = QPushButton()
        self._clear_btn.setObjectName("LinkBtn")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._clear)
        header.addWidget(self._title)
        header.addStretch()
        header.addWidget(self._clear_btn)
        layout.addLayout(header)

        self._empty = QLabel()
        self._empty.setObjectName("EmptyState")
        layout.addWidget(self._empty)

        self._list = QVBoxLayout()
        self._list.setSpacing(12)
        layout.addLayout(self._list)
        layout.addStretch()
        self.setWidget(content)

    def refresh(self) -> None:
        """Show the operations of the history again."""
        for card in self._cards:
            card.deleteLater()
        self._cards = []
        operations = get_history().operations()
        for operation in operations:
            card = OperationCard(operation, self)
            self._cards.append(card)
            self._list.addWidget(card)
        self._empty.setVisible(not operations)
        self._clear_btn.setVisible(bool(operations))

    def undo(self, operation_id: str, index: Optional[int] = None) -> None:
        """Undo an operation, or one of its files, then show the list again."""
        undo_operation(
            self, self._runner, operation_id, index, on_done=lambda _r: self.refresh()
        )

    def _clear(self) -> None:
        answer = message_box.question(
            self,
            tr("history_clear", "Clear history"),
            tr(
                "history_confirm_clear",
                "Clear the history? The renames can no longer be undone. "
                "The files stay where they are.",
            ),
        )
        if answer == message_box.StandardButton.Yes:
            get_history().clear()
            self.refresh()

    def retranslateUi(self) -> None:
        """Refresh translatable labels."""
        self._title.setText(tr("history", "History"))
        self._clear_btn.setText(tr("history_clear", "Clear history"))
        self._empty.setText(tr("history_empty", "No renames yet."))
        self.refresh()

    def stop_workers(self) -> None:
        """Stop the undo running, if any."""
        self._runner.stop()
