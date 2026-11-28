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
"""File names section: the name model of each media type, as a dotted sheet.

A line per type (Movies, TV shows, Music, Books, Games) with its model; a
click opens it to edit the model, its variables under the field. The
preview of the settings screen follows the line open, as it is typed.
"""

from string import Formatter
from typing import Dict, List, NamedTuple

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from sok.config.config_manager import AppConfig
from sok.ui.components.settings.layout import SheetRow, VariableChip
from sok.ui.i18n import tr
from sok.ui.theme import ui_font


class NameModel(NamedTuple):
    """A name model of the settings."""

    config_key: str
    tr_key: str  # word of the type, as in the navigation
    default: str
    variables: List[str]


MODELS: List[NameModel] = [
    NameModel(
        "movie_format",
        "movies",
        "Movies",
        ["title", "year", "quality"],
    ),
    NameModel(
        "video_format",
        "tv_shows",
        "TV Shows",
        ["title", "season", "episode", "episode_title"],
    ),
    NameModel(
        "music_format",
        "music",
        "Music",
        ["artist", "album", "track", "title", "year"],
    ),
    NameModel(
        "book_format",
        "books",
        "Books",
        ["author", "title", "year", "series", "series_number"],
    ),
    NameModel(
        "game_format",
        "games",
        "Games",
        ["title", "year", "platform", "tags"],
    ),
]

# Variables the engine fills without a key for them.
HIDDEN_VARIABLES: Dict[str, List[str]] = {"video_format": ["season_num", "episode_num"]}


def allowed_variables(model: "NameModel") -> List[str]:
    return model.variables + HIDDEN_VARIABLES.get(model.config_key, [])


# The models whose default gives the names Plex, Jellyfin and Kodi read.
MEDIA_SERVER_MODELS = ("movie_format", "video_format")


def default_model(config_key: str) -> str:
    """The model S.O.K uses when the setting is not changed."""
    return str(getattr(AppConfig(), config_key))


def model_error(model: str, variables: List[str]) -> str:
    """Why a model cannot be used, or "" if it can.

    A variable the type does not have stops the renaming of movies and TV
    shows, so it is refused for every type.
    """
    if not model.strip():
        return tr("settings_model_empty", "The model is empty.")
    try:
        fields = [
            f for _text, f, _spec, _conv in Formatter().parse(model) if f is not None
        ]
    except ValueError:
        return tr("pattern_error_braces", "A brace { or } is not closed.")
    for name in fields:
        if name not in variables:
            return tr("pattern_error_unknown", "Unknown variable: {name}").format(
                name="{" + name + "}"
            )
    return ""


class FormatsSection(QWidget):
    """The name model of each media type, as a dotted sheet.

    A line per type: its name, then its model in Geist Mono. A click opens
    the line: the field of the model, its variables in faint text (a click
    inserts one), why it cannot be used, and a note when it gives the names
    of Plex, Jellyfin and Kodi.

    Signals:
        model_changed(str, str): Setting and text of the model shown, at
            each key typed or line opened.
    """

    model_changed = Signal(str, str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._key = MODELS[0].config_key
        self._editing = False  # a line is open
        self._rows: Dict[str, SheetRow] = {}
        self._chips: Dict[str, QWidget] = {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for model in MODELS:
            row = SheetRow(mono_value=True)
            row.clicked.connect(lambda k=model.config_key: self._toggle(k))
            self._rows[model.config_key] = row
            layout.addWidget(row)

        # One editor, moved into the line that is open.
        self._editor = QWidget()
        editor = QVBoxLayout(self._editor)
        editor.setContentsMargins(0, 4, 0, 0)
        editor.setSpacing(8)
        self._input = QLineEdit()
        self._input.setFont(ui_font(14, 400, mono=True))
        self._input.textChanged.connect(self._typed)
        self._input.editingFinished.connect(self._save)
        editor.addWidget(self._input)
        for model in MODELS:
            line = QWidget()
            line_layout = QHBoxLayout(line)
            line_layout.setContentsMargins(0, 0, 0, 0)
            line_layout.setSpacing(12)
            for variable in model.variables:
                chip = VariableChip("{" + variable + "}")
                chip.picked.connect(self._insert)
                line_layout.addWidget(chip)
            line_layout.addStretch()
            self._chips[model.config_key] = line
            editor.addWidget(line)
        self._error = QLabel()
        self._error.setFont(ui_font(13))
        self._error.setProperty("tone", "warn")
        editor.addWidget(self._error)
        self._compatible = QLabel()
        self._compatible.setObjectName("SettingHint")
        self._compatible.setFont(ui_font(13))
        editor.addWidget(self._compatible)
        self._editor.setVisible(False)

    # ------------------------------------------------------------ Models

    def current(self) -> NameModel:
        return next(m for m in MODELS if m.config_key == self._key)

    def text(self) -> str:
        if self._editing:
            return self._input.text()
        return self._config.get(self._key, "") or ""

    def _toggle(self, config_key: str) -> None:
        """Open a line, or close it if it is the open one."""
        row = self._rows[config_key]
        self._save()
        if row.is_open():
            row.set_open(False)
            self._editor.setVisible(False)
            self._editing = False
            self._show_values()
            return
        for other in self._rows.values():
            other.set_open(False)
        self._key = config_key
        row.details_layout.addWidget(self._editor)
        for key, line in self._chips.items():
            line.setVisible(key == config_key)
        self._input.blockSignals(True)
        self._input.setText(self._config.get(config_key, "") or "")
        self._input.blockSignals(False)
        self._editor.setVisible(True)
        self._editing = True
        row.set_open(True)
        self._show_values()
        self._typed()
        self._input.setFocus()

    def _show_values(self) -> None:
        for key, row in self._rows.items():
            if not (row.is_open() and self._editing):
                row.value.setText(self._config.get(key, "") or "")

    def _typed(self, *_args) -> None:
        model = self.current()
        text = self._input.text()
        error = model_error(text, allowed_variables(model))
        self._error.setText(error)
        self._error.setVisible(bool(error))
        self._compatible.setVisible(
            not error
            and model.config_key in MEDIA_SERVER_MODELS
            and text.strip() == default_model(model.config_key)
        )
        self._rows[model.config_key].value.setText(text)
        self.model_changed.emit(model.config_key, text)

    def _save(self) -> None:
        """Save the model being edited, if it can be filled."""
        if not self._editing:
            return
        model = self.current()
        text = self._input.text().strip()
        error = model_error(text, allowed_variables(model))
        if not error and text != self._config.get(model.config_key, ""):
            self._config.set(model.config_key, text)

    def _insert(self, variable: str) -> None:
        self._input.insert(variable)
        self._input.setFocus()
        self._save()

    def load(self):
        if self._editing:
            self._input.blockSignals(True)
            self._input.setText(self._config.get(self._key, "") or "")
            self._input.blockSignals(False)
            self._typed()
        self._show_values()
        self.model_changed.emit(self._key, self.text())

    def retranslate(self):
        for model in MODELS:
            self._rows[model.config_key].name.setText(tr(model.tr_key, model.default))
        self._compatible.setText(
            tr("settings_media_servers", "Compatible with Plex, Jellyfin and Kodi")
        )
        self.load()
