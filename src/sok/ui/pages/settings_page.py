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
"""Settings Page orchestrator that composes section components."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel, QMessageBox

from sok.config.config_manager import get_config_manager
from sok.ui.components.integrations.oauth import OAuthManager
from sok.ui.components.settings.api_section import ApiSection
from sok.ui.components.settings.api_preferences_section import ApiPreferencesSection
from sok.ui.components.settings.paths_section import PathsSection
from sok.ui.components.settings.formats_section import FormatsSection
from sok.ui.components.settings.appearance_section import AppearanceSection
from sok.ui.components.settings.behavior_section import BehaviorSection
from sok.ui.components.settings.about_section import AboutSection
from sok.ui.i18n import tr


class SettingsPage(QScrollArea):
    """Settings page with reusable configuration sections.

    Composes API, paths, formats, appearance, and behavior settings
    into a unified configuration interface.

    Attributes:
        language_changed: Signal emitted with new language code.
        theme_changed: Signal emitted with dark mode state.
    """

    language_changed = Signal(str)
    theme_changed = Signal(bool)

    def __init__(self, on_toggle, parent=None):
        """Initialize the settings page.

        Args:
            on_toggle: Callback for theme toggle.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._on_toggle = on_toggle
        self._config = get_config_manager()
        self._oauth = OAuthManager()

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("Page")

        self._build()
        self._load_settings()

    def _build(self):
        """Build the settings page layout.

        Creates all setting sections and adds them to the layout.
        """
        content = QWidget()
        content.setObjectName("PageContent")
        self._main_layout = QVBoxLayout(content)
        self._main_layout.setContentsMargins(16, 12, 16, 12)
        self._main_layout.setSpacing(12)

        self.lbl_title = QLabel()
        self.lbl_title.setObjectName("PageTitle")
        self._main_layout.addWidget(self.lbl_title)

        self.api_section = ApiSection(self._config, self._oauth)
        self.api_pref_section = ApiPreferencesSection(self._config)
        self.paths_section = PathsSection(self._config)
        self.formats_section = FormatsSection(self._config)
        self.appearance_section = AppearanceSection(self._config)
        self.behavior_section = BehaviorSection(self._config)
        self.about_section = AboutSection(self._config)

        self.appearance_section.theme_changed.connect(self._on_theme_change)
        self.appearance_section.language_changed.connect(self._on_language_change)
        self.about_section.reset_requested.connect(self._on_reset)

        for section in [
            self.api_section,
            self.api_pref_section,
            self.paths_section,
            self.formats_section,
            self.appearance_section,
            self.behavior_section,
            self.about_section,
        ]:
            self._main_layout.addWidget(section)

        self._main_layout.addStretch()
        self.setWidget(content)
        self.retranslateUi()

    def retranslateUi(self):
        """Update all translatable text.

        Called after language changes to refresh UI strings.
        """
        self.lbl_title.setText(tr("settings", "Settings"))
        for section in [
            self.api_section,
            self.api_pref_section,
            self.paths_section,
            self.formats_section,
            self.appearance_section,
            self.behavior_section,
            self.about_section,
        ]:
            section.retranslate()

    def _load_settings(self):
        """Load settings into all sections.

        Populates UI with current configuration values.
        """
        for section in [
            self.api_section,
            self.api_pref_section,
            self.paths_section,
            self.formats_section,
            self.appearance_section,
            self.behavior_section,
            self.about_section,
        ]:
            section.load()

    def _on_theme_change(self, is_dark: bool):
        """Handle theme toggle from appearance section.

        Calls the toggle callback and emits theme_changed signal.

        Args:
            is_dark: True for dark theme, False for light.
        """
        self._on_toggle(is_dark)
        self.theme_changed.emit(is_dark)

    def _on_language_change(self, lang_code: str):
        """Handle language change from appearance section.

        Emits language_changed signal to trigger UI retranslation.

        Args:
            lang_code: New language code (e.g., 'en', 'fr').
        """
        self.language_changed.emit(lang_code)

    def _on_reset(self):
        """Handle reset request from about section.

        Shows confirmation dialog before resetting all settings
        to their default values.
        """
        reply = QMessageBox.question(
            self,
            tr("reset_title", "Reset"),
            tr("reset_confirm", "Are you sure you want to reset all settings?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._config.reset()
            self._load_settings()
            QMessageBox.information(
                self,
                tr("reset_done_title", "Reset"),
                tr("reset_done_msg", "Settings have been reset."),
            )
