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
"""File names section: the name model of each media type.

A row of keys picks the type (Movies, TV shows, Music, Books, Games); under
it, its model in one field and its variables, a click on one inserting it.
The preview of the settings screen follows the model as it is typed.
"""

from string import Formatter
from typing import Dict, List, NamedTuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from sok.config.config_manager import AppConfig
from sok.ui.components.settings.layout import CheckBox, Choice, VariableChip
from sok.ui.i18n import tr
from sok.ui.theme import ui_font


class NameModel(NamedTuple):
    """A name model of the settings."""

    config_key: str
    tr_key: str  # word of the type, as in the navigation
    default: str
    label_key: str
    label: str
    variables: List[str]


MODELS: List[NameModel] = [
    NameModel(
        "movie_format",
        "movies",
        "Movies",
        "settings_model_movies",
        "Model for movies",
        ["title", "year", "quality"],
    ),
    NameModel(
        "video_format",
        "tv_shows",
        "TV Shows",
        "settings_model_series",
        "Model for TV shows",
        ["title", "season", "episode", "episode_title"],
    ),
    NameModel(
        "music_format",
        "music",
        "Music",
        "settings_model_music",
        "Model for music",
        ["artist", "album", "track", "title", "year"],
    ),
    NameModel(
        "book_format",
        "books",
        "Books",
        "settings_model_books",
        "Model for books",
        ["author", "title", "year", "series", "series_number"],
    ),
    NameModel(
        "game_format",
        "games",
        "Games",
        "settings_model_games",
        "Model for games",
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
    """The name model of each media type.

    Signals:
        model_changed(str, str): Setting and text of the model shown, at
            each key typed or type chosen.
    """

    model_changed = Signal(str, str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._chips: Dict[str, QWidget] = {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self._choice = Choice([m.config_key for m in MODELS])
        self._choice.chosen.connect(self._show_model)
        layout.addWidget(self._choice)

        field = QVBoxLayout()
        field.setSpacing(8)
        self._label = QLabel()
        self._label.setObjectName("SettingMuted")
        self._label.setFont(ui_font(14))
        self._input = QLineEdit()
        self._input.setFont(ui_font(14, 400, mono=True))
        self._input.textChanged.connect(self._typed)
        self._input.editingFinished.connect(self._save)
        field.addWidget(self._label)
        field.addWidget(self._input)
        layout.addLayout(field)

        for model in MODELS:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            for variable in model.variables:
                chip = VariableChip("{" + variable + "}")
                chip.picked.connect(self._insert)
                row_layout.addWidget(chip)
            row_layout.addStretch()
            row.setVisible(False)
            self._chips[model.config_key] = row
            layout.addWidget(row)

        self._error = QLabel()
        self._error.setFont(ui_font(13))
        self._error.setProperty("tone", "warn")
        self._error.setVisible(False)
        layout.addWidget(self._error)

        # A statement, not a setting: the box cannot be clicked.
        self._compatible = QWidget()
        line = QHBoxLayout(self._compatible)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(10)
        box = CheckBox()
        box.setChecked(True)
        box.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._compatible_text = QLabel()
        self._compatible_text.setObjectName("SettingText")
        self._compatible_text.setFont(ui_font(14))
        line.addWidget(box)
        line.addWidget(self._compatible_text, 1)
        layout.addWidget(self._compatible)

        self._choice.set_value(MODELS[0].config_key)

    # ------------------------------------------------------------ Models

    def current(self) -> NameModel:
        key = self._choice.value() or MODELS[0].config_key
        return next(m for m in MODELS if m.config_key == key)

    def text(self) -> str:
        return self._input.text()

    def _show_model(self, config_key: str) -> None:
        self._save()
        self._choice.set_value(config_key)
        model = self.current()
        for key, row in self._chips.items():
            row.setVisible(key == config_key)
        self._label.setText(tr(model.label_key, model.label))
        self._input.blockSignals(True)
        self._input.setText(self._config.get(config_key, "") or "")
        self._input.blockSignals(False)
        self._typed()

    def _typed(self, *_args) -> None:
        model = self.current()
        text = self._input.text()
        error = model_error(text, allowed_variables(model))
        valid = not error
        self._error.setText(error)
        self._error.setVisible(not valid)
        self._compatible.setVisible(
            valid
            and model.config_key in MEDIA_SERVER_MODELS
            and text.strip() == default_model(model.config_key)
        )
        self.model_changed.emit(model.config_key, text)

    def _save(self) -> None:
        """Save the model shown, if it can be filled."""
        model = self.current()
        key = model.config_key
        text = self._input.text().strip()
        if not model_error(text, allowed_variables(model)) and text != self._config.get(
            key, ""
        ):
            self._config.set(key, text)

    def _insert(self, variable: str) -> None:
        self._input.insert(variable)
        self._input.setFocus()
        self._save()

    def load(self):
        self._show_model(self.current().config_key)

    def retranslate(self):
        self._choice.set_texts(tr(m.tr_key, m.default) for m in MODELS)
        self._compatible_text.setText(
            tr("settings_media_servers", "Compatible with Plex, Jellyfin and Kodi")
        )
        self.load()
