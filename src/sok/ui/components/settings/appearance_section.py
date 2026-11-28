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

A sheet like the other sections: the theme as three words (Dark, Light,
System), the chosen one in ink; the language, whose line opens on the
names of the languages.
"""

from typing import Dict

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from sok.ui.components.settings.layout import (
    Choice,
    ChoiceLine,
    SheetRow,
)
from sok.ui.i18n import tr
from sok.ui.platform import (
    SYSTEM_THEME,
    apply_color_scheme,
    system_prefers_dark,
)

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
    """Theme and language.

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
        layout.setSpacing(6)

        self._theme_line = ChoiceLine(THEMES)
        self.theme_choice = self._theme_line.choice
        self.theme_choice.chosen.connect(self._on_theme_choice)
        layout.addWidget(self._theme_line)

        # The language: its name, and once open, every language as a word.
        self._lang_row = SheetRow()
        self._lang_row.clicked.connect(
            lambda: self._lang_row.set_open(not self._lang_row.is_open())
        )
        codes = list(self._config.get_available_languages())
        self.lang_choice = Choice(codes)
        self.lang_choice.set_texts(LANGUAGE_NAMES.get(c, c.upper()) for c in codes)
        self.lang_choice.chosen.connect(self._on_language_change)
        words = QHBoxLayout()
        words.addWidget(self.lang_choice)
        words.addStretch()
        self._lang_row.details_layout.addLayout(words)
        layout.addWidget(self._lang_row)

    def _on_theme_choice(self, theme: str) -> None:
        """Save the theme chosen and show it.

        Args:
            theme: "dark", "light" or "system".
        """
        self._config.set("theme", theme)
        apply_color_scheme(theme)
        is_dark = system_prefers_dark() if theme == SYSTEM_THEME else theme == "dark"
        self.theme_changed.emit(is_dark)

    def _on_language_change(self, lang_code: str):
        self._config.set("language", lang_code)
        self._lang_row.value.setText(LANGUAGE_NAMES.get(lang_code, lang_code.upper()))
        self.language_changed.emit(lang_code)

    def load(self):
        """Load settings values into UI."""
        theme = self._config.get("theme", SYSTEM_THEME)
        # "orange", the dropped orange theme, reads as light.
        theme = "light" if theme == "orange" else theme
        self.theme_choice.set_value(theme if theme in THEMES else SYSTEM_THEME)
        code = self._config.get("language", "fr")
        self.lang_choice.set_value(code)
        self._lang_row.value.setText(LANGUAGE_NAMES.get(code, code.upper()))

    def retranslate(self):
        """Update translatable UI text."""
        self.theme_choice.set_texts(
            [
                tr("theme_dark", "Dark"),
                tr("theme_light", "Light"),
                tr("theme_system", "System"),
            ]
        )
        self._theme_line.name.setText(tr("settings_theme", "Theme"))
        self._lang_row.name.setText(tr("language", "Language"))
        self.load()
