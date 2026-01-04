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
"""Appearance section for settings page.

Provides theme selection (dark/light) and language selection controls
for customizing the application's visual appearance.
"""

from typing import Dict
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from sok.ui.components.base import Card, Toggle
from sok.ui.components.inputs import ModernComboBox
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.i18n import tr
from sok.ui.theme import card_shadow


class AppearanceSection(QWidget):
    """Appearance section for settings page.

    Provides theme selection (dark/light) and language selection controls.

    Signals:
        theme_changed: Emitted when theme is changed (True for dark).
        language_changed: Emitted with language code when language changes.
    """

    theme_changed = Signal(bool)
    language_changed = Signal(str)

    def __init__(self, config, parent=None):
        """Initialize the appearance section.

        Args:
            config: Configuration manager instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._config = config
        self._build()

    def _build(self):
        """Build the section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = make_section_label("appearance", "APPARENCE")
        layout.addWidget(self.label)

        card = Card()

        dark_row = QWidget()
        dark_row.setFixedHeight(32)
        dr_layout = QHBoxLayout(dark_row)
        dr_layout.setContentsMargins(12, 0, 12, 0)

        self.dark_lbl = QLabel()
        self.dark_lbl.setProperty("tr_key", "dark_mode")
        self.dark_lbl.setProperty("tr_default", "Mode sombre")
        self.dark_lbl.setObjectName("RowTitle")

        self.toggle = Toggle()
        self.toggle.toggled.connect(self._on_theme_change)

        dr_layout.addWidget(self.dark_lbl)
        dr_layout.addStretch()
        dr_layout.addWidget(self.toggle)

        card.add(dark_row)

        lang_row = QWidget()
        lang_row.setFixedHeight(32)
        lr_layout = QHBoxLayout(lang_row)
        lr_layout.setContentsMargins(12, 0, 12, 0)

        self.lang_lbl = QLabel()
        self.lang_lbl.setProperty("tr_key", "language")
        self.lang_lbl.setProperty("tr_default", "Langue")
        self.lang_lbl.setObjectName("RowTitle")

        self.lang_combo = ModernComboBox()
        self.lang_combo.setMinimumWidth(120)
        self.lang_combo.setObjectName("SettingsCombo")

        lang_names: Dict[str, str] = {
            "fr": "Français",
            "en": "English",
            "de": "Deutsch",
            "es": "Español",
            "it": "Italiano",
            "pt": "Português",
            "ru": "Русский",
            "pl": "Polski",
        }
        for code in self._config.get_available_languages():
            name = lang_names.get(code, code.upper())
            self.lang_combo.addItem(name, code)

        self.lang_combo.currentIndexChanged.connect(self._on_language_change)

        lr_layout.addWidget(self.lang_lbl)
        lr_layout.addStretch()
        lr_layout.addWidget(self.lang_combo)

        card.add(lang_row)

        card.setGraphicsEffect(card_shadow())
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(card)

    def _on_theme_change(self, is_dark: bool):
        """Handle theme toggle change.

        Args:
            is_dark: True for dark theme.
        """
        self._config.set("theme", "dark" if is_dark else "light")
        self.theme_changed.emit(is_dark)

    def _on_language_change(self, index: int):
        """Handle language combo change.

        Args:
            index: Selected combo box index.
        """
        lang_code = self.lang_combo.itemData(index)
        if lang_code:
            self._config.set("language", lang_code)
            self.language_changed.emit(lang_code)

    def load(self):
        """Load settings values into UI."""
        is_dark = self._config.get("theme", "dark") == "dark"
        self.toggle.blockSignals(True)
        self.toggle.setChecked(is_dark)
        self.toggle.blockSignals(False)

        current_lang = self._config.get("language", "fr")
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == current_lang:
                self.lang_combo.blockSignals(True)
                self.lang_combo.setCurrentIndex(i)
                self.lang_combo.blockSignals(False)
                break

    def retranslate(self):
        """Update translatable UI text."""
        self.label.setText(tr("appearance", "APPEARANCE"))
        self.dark_lbl.setText(tr("dark_mode", "Dark Mode"))
        self.lang_lbl.setText(tr("language", "Language"))
        self.load()
