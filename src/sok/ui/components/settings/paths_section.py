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
"""Default paths section for settings page.

Provides folder selection controls for setting default destination
paths for each media type (videos, music, books, games).
"""

from typing import Dict
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFileDialog,
    QSizePolicy,
)
from sok.ui.components.base import Card, ActionButton
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.i18n import tr
from sok.ui.theme import card_shadow


class PathsSection(QWidget):
    """Default paths section for settings page.

    Provides folder selection controls for setting default destination
    paths for each media type (videos, music, books, games).
    """

    def __init__(self, config, parent=None):
        """Initialize the paths section.

        Args:
            config: Configuration manager instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._config = config
        self._path_labels: Dict[str, QLabel] = {}
        self._title_labels: Dict[str, QLabel] = {}
        self._browse_buttons: Dict[str, ActionButton] = {}
        self._build()

    def _build(self):
        """Build the section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = make_section_label("default_folders", "DEFAULT FOLDERS")
        layout.addWidget(self.label)

        card = Card()
        for tr_key, default, config_key in [
            ("videos", "Videos", "default_video_path"),
            ("music", "Music", "default_music_path"),
            ("books", "Books", "default_books_path"),
            ("games", "Games", "default_games_path"),
        ]:
            card.add(self._create_path_row(tr_key, default, config_key))

        card.setGraphicsEffect(card_shadow())
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(card)

    def _create_path_row(self, tr_key: str, default: str, config_key: str) -> QWidget:
        """Create a row with path display and browse button.

        Args:
            tr_key: Translation key for the label.
            default: Default label text.
            config_key: Configuration key for the path.

        Returns:
            Widget containing the row.
        """
        row = QWidget()
        row.setFixedHeight(44)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 0, 12, 0)

        title_lbl = QLabel()
        title_lbl.setProperty("tr_key", tr_key)
        title_lbl.setProperty("tr_default", default)
        title_lbl.setObjectName("RowTitle")

        path_lbl = QLabel()
        path_lbl.setObjectName("RowValue")
        path_lbl.setProperty("config_key", config_key)
        self._path_labels[config_key] = path_lbl
        self._title_labels[config_key] = title_lbl

        browse_btn = ActionButton("")
        browse_btn.setProperty("tr_key", "browse")
        browse_btn.setProperty("tr_default", "Browse")
        browse_btn.setText(tr("browse", "Browse"))
        browse_btn.clicked.connect(lambda: self._browse_path(config_key))
        self._browse_buttons[config_key] = browse_btn

        layout.addWidget(title_lbl)
        layout.addStretch()
        layout.addWidget(path_lbl)
        layout.addWidget(browse_btn)
        return row

    def _browse_path(self, key: str):
        """Open folder browser dialog.

        Args:
            key: Configuration key for the path.
        """
        current = self._config.get(key, "")
        path = QFileDialog.getExistingDirectory(
            self, tr("choose_folder", "Choose a folder"), current
        )
        if path:
            self._config.set(key, path)
            self._update_path_label(key, path)

    def _update_path_label(self, key: str, path: str):
        """Update the path label with truncation.

        Args:
            key: Configuration key.
            path: Full path to display.
        """
        label = self._path_labels.get(key)
        if label:
            display = path if len(path) < 40 else f"...{path[-37:]}"
            label.setText(display)

    def load(self):
        """Load settings values into UI."""
        for key, label in self._path_labels.items():
            path = self._config.get(key, "")
            label.setText(path if path else tr("not_defined", "Not defined"))

    def retranslate(self):
        """Update translatable UI text."""
        self.label.setText(tr("default_folders", "DEFAULT FOLDERS"))
        for key, title_lbl in self._title_labels.items():
            tr_key = title_lbl.property("tr_key")
            default = title_lbl.property("tr_default")
            if tr_key:
                title_lbl.setText(tr(tr_key, default or ""))
        for btn in self._browse_buttons.values():
            tr_key = btn.property("tr_key")
            tr_default = btn.property("tr_default")
            if tr_key:
                btn.setText(tr(tr_key, tr_default or ""))
        self.load()
