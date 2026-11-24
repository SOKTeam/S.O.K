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
"""Settings page, from mockup 07 of the art direction.

On the left, the title "Settings." and the sections, each a title in a
200px column and its settings on the right, under a hairline:
Destinations, File names, Sources, Appearance, Behavior, Input formats,
About. On the right, the live preview of the name model being edited.
"""

from __future__ import annotations

from typing import List, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sok.config.config_manager import get_config_manager
from sok.ui import message_box
from sok.ui.components.integrations.oauth import OAuthManager
from sok.ui.components.settings.about_section import AboutSection
from sok.ui.components.settings.api_section import ApiSection
from sok.ui.components.settings.appearance_section import AppearanceSection
from sok.ui.components.settings.behavior_section import BehaviorSection
from sok.ui.components.settings.formats_section import FormatsSection
from sok.ui.components.settings.input_formats_section import InputFormatsSection
from sok.ui.components.settings.layout import SettingsBlock, settings_stylesheet
from sok.ui.components.settings.paths_section import PathsSection
from sok.ui.components.settings.preview import SettingsPreview
from sok.ui.i18n import tr
from sok.ui.responsive import fit_display, side_width
from sok.ui.theme import Theme, ui_font

# The folder setting of the type of each name model, for the preview.
MODEL_FOLDERS = {
    "movie_format": ("default_video_path",),
    "video_format": ("default_series_path", "default_video_path"),
    "music_format": ("default_music_path",),
    "book_format": ("default_books_path",),
    "game_format": ("default_games_path",),
}


# Narrowest page that still shows the preview, and narrowest left column
# with the titles of the sections at the left of their settings.
PREVIEW_MIN_WIDTH = 1000
COMPACT_WIDTH = 760


def _palette(widget: QWidget) -> dict[str, str]:
    return getattr(widget.window(), "c", None) or Theme.DARK


class SettingsPage(QWidget):
    """The settings, by section, with the preview of the name models.

    Attributes:
        language_changed: Signal emitted with new language code.
        theme_changed: Signal emitted with dark mode state.
    """

    language_changed = Signal(str)
    theme_changed = Signal(bool)
    # The light of the page moved: the window paints it again.
    light_changed = Signal()

    def __init__(self, on_toggle, parent=None):
        """Initialize the settings page.

        Args:
            on_toggle: Callback for theme toggle.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setObjectName("Page")
        self._on_toggle = on_toggle
        self._config = get_config_manager()
        self._oauth = OAuthManager()
        self._build()
        self._load_settings()

    def _build(self):
        columns = QHBoxLayout(self)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")
        self._content = QWidget()
        self._content.setObjectName("SettingsContent")
        self._content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        left = QVBoxLayout(self._content)
        left.setContentsMargins(26, 40, 40, 28)
        left.setSpacing(0)
        scroll.setWidget(self._content)
        self._scroll = scroll

        self.lbl_title = QLabel()
        title = ui_font(52, 650)
        title.setLetterSpacing(title.SpacingType.AbsoluteSpacing, -2.08)
        self.lbl_title.setFont(title)
        self.lbl_title.setContentsMargins(14, 0, 14, 20)
        left.addWidget(self.lbl_title)

        self.paths_section = PathsSection(self._config)
        self.formats_section = FormatsSection(self._config)
        self.api_section = ApiSection(self._config, self._oauth)
        self.appearance_section = AppearanceSection(self._config)
        self.behavior_section = BehaviorSection(self._config)
        self.input_formats_section = InputFormatsSection(self._config)
        self.about_section = AboutSection(self._config)

        sources = QWidget()
        sources_layout = QVBoxLayout(sources)
        sources_layout.setContentsMargins(0, 0, 0, 0)
        sources_layout.setSpacing(14)
        self._sources_note = QLabel()
        self._sources_note.setObjectName("SettingHint")
        self._sources_note.setWordWrap(True)
        sources_layout.addWidget(self.api_section)
        sources_layout.addWidget(self._sources_note)

        # (translation key, default, body) of each section, in order.
        self._blocks: List[Tuple[str, str, SettingsBlock]] = []
        for tr_key, default, body in (
            ("settings_destinations", "Destinations", self.paths_section),
            ("settings_file_names", "File names", self.formats_section),
            ("settings_sources", "Sources", sources),
            ("appearance", "Appearance", self.appearance_section),
            ("behavior", "Behavior", self.behavior_section),
            ("input_formats", "Input Formats", self.input_formats_section),
            ("about", "About", self.about_section),
        ):
            block = SettingsBlock(body)
            self._blocks.append((tr_key, default, block))
            left.addWidget(block)
        left.addStretch()
        columns.addWidget(scroll, 1)

        self._preview = SettingsPreview()
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setFrameShape(QFrame.Shape.NoFrame)
        preview_scroll.setFixedWidth(side_width(1440))
        preview_scroll.setWidget(self._preview)
        columns.addWidget(preview_scroll)
        self._preview_scroll = preview_scroll
        preview_scroll.viewport().setStyleSheet("background: transparent;")
        self._preview.light_changed.connect(self.light_changed.emit)
        preview_scroll.verticalScrollBar().valueChanged.connect(self.light_changed.emit)

        self.appearance_section.theme_changed.connect(self._on_theme_change)
        self.appearance_section.language_changed.connect(self._on_language_change)
        self.about_section.reset_requested.connect(self._on_reset)
        self.formats_section.model_changed.connect(self._show_preview)
        self.paths_section.changed.connect(self._refresh_preview)

        self.retranslateUi()

    def _sections(self):
        return [
            self.paths_section,
            self.formats_section,
            self.api_section,
            self.appearance_section,
            self.behavior_section,
            self.input_formats_section,
            self.about_section,
        ]

    def retranslateUi(self):
        """Update all translatable text."""
        self.lbl_title.setText(tr("settings_title", "Settings."))
        for tr_key, default, block in self._blocks:
            block.title.setText(tr(tr_key, default))
        self._sources_note.setText(
            tr(
                "settings_sources_note",
                "Only titles are sent. Your files stay on your computer.",
            )
        )
        self._preview.retranslate()
        for section in self._sections():
            section.retranslate()

    def _load_settings(self):
        for section in self._sections():
            section.load()

    # ----------------------------------------------------------- Preview

    def _show_preview(self, config_key: str, model: str) -> None:
        folder = ""
        for key in MODEL_FOLDERS.get(config_key, ()):
            folder = self._config.get(key, "") or ""
            if folder:
                break
        self._preview.show_model(config_key, model, folder)

    def _refresh_preview(self) -> None:
        model = self.formats_section.current()
        self._show_preview(model.config_key, self.formats_section.text())

    # ------------------------------------------------------------- Style

    def resizeEvent(self, e):  # noqa: N802 - Qt API
        """The preview leaves a narrow window, and the titles of the sections
        go above their settings when the room is short."""
        super().resizeEvent(e)
        width = self.width()
        show_preview = width >= PREVIEW_MIN_WIDTH
        self._preview_scroll.setVisible(show_preview)
        if show_preview:
            self._preview_scroll.setFixedWidth(side_width(width))
        left = width - (side_width(width) if show_preview else 0)
        for _key, _default, block in self._blocks:
            block.set_compact(left < COMPACT_WIDTH)
        fit_display([self.lbl_title], width)
        self.light_changed.emit()

    def light_source(self):
        """The widget whose light the window paints, or None (see
        main_window.LightColumn)."""
        return self._preview if self._preview_scroll.isVisible() else None

    def _restyle(self) -> None:
        c = _palette(self)
        self._content.setStyleSheet(settings_stylesheet(c, "SettingsContent"))
        self.lbl_title.setStyleSheet(f"color: {c['ink']}; background: transparent;")

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            self._restyle()

    # ----------------------------------------------------------- Actions

    def _on_theme_change(self, is_dark: bool):
        self._on_toggle(is_dark)
        self.theme_changed.emit(is_dark)

    def _on_language_change(self, lang_code: str):
        self.language_changed.emit(lang_code)

    def _on_reset(self):
        """Reset every setting; the About section already asked."""
        self._config.reset()
        self._load_settings()
        self._refresh_preview()
        message_box.information(
            self,
            tr("reset_done_title", "Reset"),
            tr("reset_done_msg", "Settings have been reset."),
        )
