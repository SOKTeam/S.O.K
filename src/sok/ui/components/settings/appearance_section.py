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

Three keys pick the theme (Dark, Light, System), the chosen one in the
accent; on macOS a switch uses the accent color of the system; then the
language.
"""

from typing import Dict, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from sok.ui.components.inputs import ModernComboBox
from sok.ui.components.settings.layout import Switch, SwitchLine, Choice, Lines
from sok.ui.i18n import tr
from sok.ui.platform import (
    IS_MACOS,
    SYSTEM_THEME,
    apply_color_scheme,
    system_prefers_dark,
)
from sok.ui.theme import ui_font

THEMES = ("dark", "light", SYSTEM_THEME)

LANGUAGE_NAMES: Dict[str, str] = {
    "fr": "Français",
    "en": "English",
    "de": "Deutsch",
    "es": "Español",
    "it": "Italiano",
    "pt": "Português",
    "ru": "Русский",
    "pl": "Polski",
}


class AppearanceSection(QWidget):
    """Theme, system accent (macOS) and language.

    Signals:
        theme_changed(bool): The theme to show now, True for dark.
        language_changed(str): The language code chosen.
    """

    theme_changed = Signal(bool)
    language_changed = Signal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lines = Lines()
        layout.addWidget(lines)

        self.theme_choice = Choice(THEMES)
        self.theme_choice.chosen.connect(self._on_theme_choice)
        lines.add(self.theme_choice)

        # macOS only: use the accent color chosen in the system settings.
        self._accent_line: Optional[SwitchLine] = None
        self.accent_toggle: Optional[Switch] = None
        if IS_MACOS:
            self._accent_line = SwitchLine()
            self.accent_toggle = self._accent_line.box
            self.accent_toggle.toggled.connect(self._on_accent_change)
            lines.add(self._accent_line)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 4, 0, 0)
        row_layout.setSpacing(12)
        self.lang_lbl = QLabel()
        self.lang_lbl.setObjectName("SettingMuted")
        self.lang_lbl.setFont(ui_font(14))
        self.lang_combo = ModernComboBox()
        self.lang_combo.setMinimumWidth(160)
        self.lang_combo.setObjectName("SettingsCombo")
        for code in self._config.get_available_languages():
            self.lang_combo.addItem(LANGUAGE_NAMES.get(code, code.upper()), code)
        self.lang_combo.currentIndexChanged.connect(self._on_language_change)
        row_layout.addWidget(self.lang_lbl)
        row_layout.addWidget(self.lang_combo)
        row_layout.addStretch()
        lines.add(row)

    def _on_theme_choice(self, theme: str) -> None:
        """Save the theme chosen and show it.

        Args:
            theme: "dark", "light" or "system".
        """
        self._config.set("theme", theme)
        apply_color_scheme(theme)
        is_dark = system_prefers_dark() if theme == SYSTEM_THEME else theme == "dark"
        self.theme_changed.emit(is_dark)

    def _on_accent_change(self, use_system: bool):
        """Use the accent color of the system or the coral (macOS)."""
        self._config.set("use_system_accent", use_system)
        theme = self._config.get("theme", SYSTEM_THEME)
        is_dark = system_prefers_dark() if theme == SYSTEM_THEME else theme == "dark"
        self.theme_changed.emit(is_dark)

    def _on_language_change(self, index: int):
        lang_code = self.lang_combo.itemData(index)
        if lang_code:
            self._config.set("language", lang_code)
            self.language_changed.emit(lang_code)

    def load(self):
        """Load settings values into UI."""
        theme = self._config.get("theme", SYSTEM_THEME)
        # "orange", the dropped orange theme, reads as light.
        theme = "light" if theme == "orange" else theme
        self.theme_choice.set_value(theme if theme in THEMES else SYSTEM_THEME)
        if self.accent_toggle:
            self.accent_toggle.blockSignals(True)
            self.accent_toggle.setChecked(bool(self._config.get("use_system_accent")))
            self.accent_toggle.blockSignals(False)
        index = self.lang_combo.findData(self._config.get("language", "fr"))
        if index >= 0:
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(index)
            self.lang_combo.blockSignals(False)

    def retranslate(self):
        """Update translatable UI text."""
        self.theme_choice.set_texts(
            [
                tr("theme_dark", "Dark"),
                tr("theme_light", "Light"),
                tr("theme_system", "System"),
            ]
        )
        if self._accent_line:
            self._accent_line.label.setText(
                tr("use_system_accent", "Use system accent color")
            )
        self.lang_lbl.setText(tr("language", "Language"))
        self.load()
