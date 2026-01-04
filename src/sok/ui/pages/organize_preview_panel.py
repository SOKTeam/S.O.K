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
"""Preview panel widget extracted from OrganizePage."""

from pathlib import Path
from typing import Callable, Iterable, Protocol

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from sok.ui.components.base import Card
from sok.ui.components.window import StopPropagationScrollArea
from sok.ui.controllers.ui_state import set_empty_state
from sok.ui.theme import card_shadow


class PreviewRow(Protocol):
    """Protocol for preview row widgets.

    Defines the interface for widgets that can display file preview
    rows with editable new names.
    """

    def set_new_name(self, name: str) -> None:
        """Set the computed new name for display.

        Args:
            name: The computed new filename.
        """
        ...


class PreviewPanel(QWidget):
    """Widget for rendering file preview rows.

    Displays a scrollable list of file preview rows showing
    original and computed new filenames.

    Attributes:
        _file_rows: List of (file_path, row_widget) tuples.
    """

    def __init__(self, parent: QWidget | None = None):
        """Initialize the preview panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._file_rows: list[tuple[Path, PreviewRow]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._preview_container = Card()
        self._preview_container.setMinimumWidth(320)
        self._preview_container.setMaximumHeight(400)
        self._preview_container.setGraphicsEffect(card_shadow())

        preview_scroll = StopPropagationScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setFrameShape(QFrame.Shape.NoFrame)
        preview_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        preview_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        preview_scroll.setStyleSheet("background: transparent;")

        self._preview_card = Card()
        self._preview_card.setObjectName("InnerCard")

        preview_scroll.setWidget(self._preview_card)
        self._preview_container._layout.addWidget(preview_scroll)

        layout.addWidget(self._preview_container)
        layout.addStretch()

    def clear(self) -> None:
        """Remove all preview rows.

        Clears the preview layout and file rows list.
        """
        _clear_layout(self._preview_card._layout)
        self._file_rows.clear()

    def set_empty(self, text: str, height: int = 200) -> None:
        """Display empty state message.

        Args:
            text: Message to display.
            height: Minimum height for the empty state.
        """
        self.clear()
        set_empty_state(self._preview_card._layout, text)

    def render_preview(
        self, rows: Iterable[tuple[Path, PreviewRow]], more_label: QWidget | None
    ) -> None:
        """Render preview rows in the panel.

        Args:
            rows: Iterable of (file_path, row_widget) tuples.
            more_label: Optional label showing count of additional files.
        """
        self.clear()
        for file_path, row in rows:
            self._file_rows.append((file_path, row))
            self._preview_card.add(row)  # type: ignore[arg-type]
        if more_label:
            self._preview_card.add(more_label, last=True)

    def update_new_names(self, compute_new_name: Callable[[Path], str]) -> None:
        """Update computed new names for all preview rows.

        Args:
            compute_new_name: Function to compute new name from file path.
        """
        for file_path, row in self._file_rows:
            row.set_new_name(compute_new_name(file_path))

    @property
    def file_rows(self) -> list[tuple[Path, PreviewRow]]:
        """Get the list of file preview rows.

        Returns:
            List of (file_path, row_widget) tuples.
        """
        return list(self._file_rows)


def _clear_layout(layout) -> None:
    """Remove all items from a layout.

    Args:
        layout: Qt layout to clear.
    """
    while layout.count() > 0:
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
