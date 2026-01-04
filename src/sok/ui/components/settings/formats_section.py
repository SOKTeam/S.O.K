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
"""File formats section for settings page.

Allows users to customize the naming templates used when organizing
media files (TV series, movies, music).
"""

from typing import Dict
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
)
from sok.ui.components.base import Card
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.i18n import tr
from sok.ui.theme import card_shadow


class FormatsSection(QWidget):
    """File formats section for settings page.

    Allows users to customize the naming templates used when
    organizing media files (TV series, movies, music).
    """

    def __init__(self, config, parent=None):
        """Initialize the formats section.

        Args:
            config: Configuration manager instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._config = config
        self._inputs: Dict[str, QLineEdit] = {}
        self._build()

    def _build(self):
        """Build the section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = make_section_label("file_formats", "FILE FORMATS")
        layout.addWidget(self.label)

        card = Card()
        card.add(
            self._create_format_row(
                "tv_series",
                "TV Series",
                "{title} S{season}E{episode} {episode_title}",
                "video_format",
                "Variables: {title}, {season}, {episode}, {episode_title}",
            )
        )
        card.add(
            self._create_format_row(
                "movie",
                "Movies",
                "{title} ({year})",
                "movie_format",
                "Variables: {title}, {year}, {quality}",
            )
        )
        card.add(
            self._create_format_row(
                "music",
                "Music",
                "{track} - {title}",
                "music_format",
                "Variables: {artist}, {album}, {track}, {title}, {year}",
            )
        )

        card.setGraphicsEffect(card_shadow())
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(card)

    def _create_format_row(
        self, tr_key: str, default: str, placeholder: str, config_key: str, hint: str
    ) -> QWidget:
        """Create a row with format input.

        Args:
            tr_key: Translation key for the label.
            default: Default label text.
            placeholder: Input placeholder text.
            config_key: Configuration key for the format.
            hint: Hint text showing available variables.

        Returns:
            Widget containing the row.
        """
        row = QWidget()
        row.setFixedHeight(60)
        layout = QVBoxLayout(row)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title_lbl = QLabel()
        title_lbl.setProperty("tr_key", tr_key)
        title_lbl.setProperty("tr_default", default)
        title_lbl.setObjectName("RowTitle")

        hint_lbl = QLabel(hint)
        hint_lbl.setObjectName("RowSubtitle")

        header.addWidget(title_lbl)
        header.addStretch()
        header.addWidget(hint_lbl)
        layout.addLayout(header)

        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        input_field.setObjectName("SettingsFormatInput")
        input_field.setProperty("config_key", config_key)
        input_field.editingFinished.connect(
            lambda: self._config.set(config_key, input_field.text())
        )
        self._inputs[config_key] = input_field

        layout.addWidget(input_field)
        return row

    def load(self):
        """Load settings values into UI."""
        for key, input_field in self._inputs.items():
            input_field.setText(self._config.get(key, ""))

    def retranslate(self):
        """Update translatable UI text."""
        self.label.setText(tr("file_formats", "FILE FORMATS"))
        for input_field in self._inputs.values():
            row = input_field.parentWidget()
            if not row:
                continue
            row_layout = row.layout()
            if not row_layout:
                continue
            header_layout_item = row_layout.itemAt(0)
            header_layout = header_layout_item.layout() if header_layout_item else None
            if header_layout:
                title_item = header_layout.itemAt(0)
                title_lbl = title_item.widget() if title_item else None
                if title_lbl and hasattr(title_lbl, "setText"):
                    tr_key = title_lbl.property("tr_key")
                    default = title_lbl.property("tr_default")
                    title_lbl.setText(tr(tr_key, default or ""))  # type: ignore[union-attr]
        self.load()
