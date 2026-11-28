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
"""Destinations section: the default folder of each media type.

One line per type of the navigation (Movies, TV shows, Music, Books,
Games): its name, the folder in Geist Mono and a "Change" key. TV shows
go with the movies until they get a folder of their own.
"""

from typing import Dict, List, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QSizePolicy, QWidget

from sok.ui.components.base import KeyButton
from sok.ui.components.settings.layout import Lines
from sok.ui.i18n import tr
from sok.ui.theme import ui_font

# (translation key, default, setting) of each line, in the navigation order.
DESTINATIONS: List[Tuple[str, str, str]] = [
    ("movies", "Movies", "default_video_path"),
    ("tv_shows", "TV Shows", "default_series_path"),
    ("music", "Music", "default_music_path"),
    ("books", "Books", "default_books_path"),
    ("games", "Games", "default_games_path"),
]


class PathLabel(QLabel):
    """A folder in Geist Mono, shortened in the middle when too long."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingPath")
        self.setFont(ui_font(13, 400, mono=True))
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._full = ""

    def set_path(self, text: str, empty: bool = False) -> None:
        self._full = text
        self.setToolTip(text if not empty else "")
        self.setProperty("empty", "true" if empty else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self._elide()

    def resizeEvent(self, e):  # noqa: N802 - Qt API
        super().resizeEvent(e)
        self._elide()

    def _elide(self) -> None:
        text = self.fontMetrics().elidedText(
            self._full, Qt.TextElideMode.ElideMiddle, max(40, self.width())
        )
        if text != self.text():
            self.setText(text)


class PathsSection(QWidget):
    """The default folder of each media type.

    Signals:
        changed: A folder was chosen (the preview shows it).
    """

    changed = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._names: Dict[str, QLabel] = {}
        self._paths: Dict[str, PathLabel] = {}
        self._keys: List[KeyButton] = []
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lines = Lines()
        layout.addWidget(lines)
        for tr_key, default, config_key in DESTINATIONS:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            name = QLabel()
            name.setObjectName("SettingMuted")
            name.setFont(ui_font(14))
            name.setFixedWidth(86)
            name.setProperty("tr_key", tr_key)
            name.setProperty("tr_default", default)
            path = PathLabel()
            key = KeyButton("", small=True)
            key.clicked.connect(lambda _=False, k=config_key: self._browse_path(k))
            row_layout.addWidget(name)
            row_layout.addWidget(path, 1)
            row_layout.addWidget(key)
            self._names[config_key] = name
            self._paths[config_key] = path
            self._keys.append(key)
            lines.add(row)

    def _browse_path(self, key: str):
        current = self._config.get(key, "") or self._config.get(
            "default_video_path", ""
        )
        path = QFileDialog.getExistingDirectory(
            self, tr("choose_folder", "Choose a folder"), current
        )
        if path:
            self._config.set(key, path)
            self.load()
            self.changed.emit()

    def load(self):
        """Show the folders of the settings."""
        for key, label in self._paths.items():
            path = self._config.get(key, "")
            if path:
                label.set_path(path)
            elif key == "default_series_path" and self._config.get(
                "default_video_path", ""
            ):
                label.set_path(tr("settings_same_as_movies", "Same as movies"), True)
            else:
                label.set_path(tr("not_defined", "Not defined"), True)

    def retranslate(self):
        for label in self._names.values():
            label.setText(tr(label.property("tr_key"), label.property("tr_default")))
        for key in self._keys:
            key.setText(tr("change", "Change"))
        self.load()
