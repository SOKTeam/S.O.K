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
Preview Components - File rows for organization preview
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy

from sok.ui.theme import Theme, svg_icon


class FileRow(QWidget):
    """Row representing a file in the preview list.

    Displays original filename, arrow, and new filename with
    color coding for changed files.

    Attributes:
        filename: Original filename.
        new_name: New filename after processing.
        info: Additional file information dictionary.
    """

    def __init__(self, filename: str, new_name: str, info: dict, parent=None):
        """Initialize the file row.

        Args:
            filename: Original filename.
            new_name: New filename after processing.
            info: Additional file information.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.filename = filename
        self.new_name = new_name
        self.info = info

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(16, 16)
        self.icon_lbl.setPixmap(svg_icon("file", "#B3B3B3", 14))
        layout.addWidget(self.icon_lbl)

        self.name_lbl = QLabel(filename)
        self.name_lbl.setStyleSheet(
            f"color: {Theme.DARK['secondary']}; font-size: 12px;"
        )
        self.name_lbl.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.name_lbl, 1)

        self.arrow_lbl = QLabel("→")
        self.arrow_lbl.setStyleSheet(
            f"color: {Theme.DARK['tertiary']}; font-weight: bold;"
        )
        layout.addWidget(self.arrow_lbl)

        self.new_name_lbl = QLabel(new_name if new_name else "...")
        self.new_name_lbl.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        layout.addWidget(self.new_name_lbl, 1)

        self.setFixedHeight(36)
        self._update_style()

    def set_new_name(self, name: str):
        """Update the new filename display.

        Args:
            name: New filename to display.
        """
        self.new_name = name
        self.new_name_lbl.setText(name if name else "...")
        self._update_style()

    def _update_style(self):
        """Update styling based on filename change status."""
        # Green if changed and valid, grey otherwise
        if self.new_name and self.new_name != self.filename:
            self.new_name_lbl.setStyleSheet(
                f"color: {Theme.DARK['green']}; font-weight: bold; font-size: 12px;"
            )
            self.arrow_lbl.setStyleSheet(
                f"color: {Theme.DARK['green']}; font-weight: bold;"
            )
        else:
            self.new_name_lbl.setStyleSheet(
                f"color: {Theme.DARK['tertiary']}; font-size: 12px; font-style: italic;"
            )
            self.arrow_lbl.setStyleSheet(f"color: {Theme.DARK['tertiary']};")

    def resizeEvent(self, event):
        """Handle resize event.

        Args:
            event: Resize event (unused).
        """
        pass
