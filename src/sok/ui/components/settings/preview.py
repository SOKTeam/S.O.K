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
"""Live preview of the settings screen: an example file before and after.

The scene shows an example of the type whose name model is open: its
stand-in on the floor, the file name it has, and the path it would get
with the model typed, the parts filled by S.O.K in the accent. The name
is made the way the renaming makes it (fill_format, format_name).
"""

from __future__ import annotations

import html
import os
from dataclasses import dataclass, field
from typing import Dict, List

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from sok.core.utils import fill_format, format_name
from sok.ui.components.base import parse_color
from sok.ui.components.media_visual import standin_colors
from sok.ui.components.scene import SceneItem, Shape, _Stage, paint_light
from sok.ui.i18n import tr
from sok.ui.theme import Theme, ui_font

# Marks around a filled value, turned into accent spans afterwards.
_OPEN, _CLOSE = "\x01", "\x02"


@dataclass
class Example:
    """An example file of a type, and the values S.O.K would find."""

    title: str
    year: str
    shape: Shape
    before: str
    values: Dict[str, str]
    extension: str
    folders_in_model: bool = False  # music: "/" in the model makes folders
    folders: List[str] = field(default_factory=list)  # before the name


EXAMPLES: Dict[str, Example] = {
    "movie_format": Example(
        "Oppenheimer",
        "2023",
        Shape.POSTER,
        "oppenheimer.2023.2160p.mkv",
        {"title": "Oppenheimer", "year": "2023", "quality": "2160p"},
        ".mkv",
    ),
    "video_format": Example(
        "Severance",
        "2022",
        Shape.POSTER,
        "severance.s02e01.1080p.mkv",
        {
            "title": "Severance",
            "season": "02",
            "episode": "01",
            "episode_title": "Hello, Ms. Cobel",
            "season_num": "2",
            "episode_num": "1",
        },
        ".mkv",
        folders=["Severance", "{season} 2"],
    ),
    "music_format": Example(
        "Discovery",
        "2001",
        Shape.COVER,
        "01 one more time.flac",
        {
            "artist": "Daft Punk",
            "album": "Discovery",
            "track": "01",
            "title": "One More Time",
            "year": "2001",
        },
        ".flac",
        folders_in_model=True,
    ),
    "book_format": Example(
        "Dune",
        "1965",
        Shape.BOOK,
        "dune_frank_herbert.epub",
        {"author": "Frank Herbert", "title": "Dune", "year": "1965"},
        ".epub",
    ),
    "game_format": Example(
        "Celeste",
        "2018",
        Shape.POSTER,
        "Celeste (Europe).nsp",
        {"title": "Celeste", "year": "2018", "platform": "Switch", "tags": "(Europe)"},
        ".nsp",
    ),
}


def preview_parts(config_key: str, model: str) -> List[str]:
    """Folders and file name the example gets with a model.

    The values filled are between _OPEN and _CLOSE. An empty list means
    the model gives no name.
    """
    example = EXAMPLES[config_key]
    marked = {k: f"{_OPEN}{v}{_CLOSE}" for k, v in example.values.items()}
    pieces = model.split("/") if example.folders_in_model else [model]
    parts = [format_name(fill_format(piece, marked)) for piece in pieces]
    parts = [p for p in parts if p.strip(_OPEN + _CLOSE)]
    if not parts:
        return []
    parts[-1] += example.extension
    return parts


def _rich(text: str, accent: str) -> str:
    """Escape a path and color its filled values."""
    out = html.escape(text)
    return out.replace(_OPEN, f"<span style='color: {accent}'>").replace(
        _CLOSE, "</span>"
    )


def _palette(widget: QWidget) -> dict[str, str]:
    return getattr(widget.window(), "c", None) or Theme.DARK


class SettingsPreview(QWidget):
    """The right column of the settings: the example before and after."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key = "movie_format"
        self._model = ""
        self._destination = ""
        self._color = QColor(128, 128, 128)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 72, 44, 36)
        layout.setSpacing(32)

        self._label = QLabel()
        label = ui_font(11, 600)
        label.setLetterSpacing(label.SpacingType.AbsoluteSpacing, 0.88)
        label.setCapitalization(label.Capitalization.AllUppercase)
        self._label.setFont(label)
        layout.addWidget(self._label)

        self._stage = _Stage()
        layout.addWidget(self._stage)

        texts = QVBoxLayout()
        texts.setSpacing(16)
        self._before_lbl, self._before = self._pair(texts)
        self._after_lbl, self._after = self._pair(texts)
        self._after.setTextFormat(Qt.TextFormat.RichText)
        layout.addLayout(texts)
        layout.addStretch()
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    @staticmethod
    def _pair(layout: QVBoxLayout) -> tuple[QLabel, QLabel]:
        box = QVBoxLayout()
        box.setSpacing(6)
        name = QLabel()
        name.setFont(ui_font(13))
        value = QLabel()
        value.setFont(ui_font(13, 400, mono=True))
        value.setWordWrap(True)
        value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        box.addWidget(name)
        box.addWidget(value)
        layout.addLayout(box)
        return name, value

    def show_model(self, config_key: str, model: str, destination: str) -> None:
        """Show the example of a type with a model.

        Args:
            config_key: Setting of the model ("movie_format"…).
            model: The model as typed.
            destination: Folder of the type in the settings ("" for none).
        """
        changed = config_key != self._key or not self._stage.object_rect().isValid()
        self._key, self._model, self._destination = config_key, model, destination
        if changed:
            example = EXAMPLES[config_key]
            self._color = standin_colors(example.title)[0]
            self._stage.set_item(
                SceneItem(example.title, year=example.year, shape=example.shape),
                self._color,
            )
        self._show_texts()
        self.update()

    def _show_texts(self) -> None:
        c = _palette(self)
        example = EXAMPLES[self._key]
        self._before.setText(example.before)
        parts = preview_parts(self._key, self._model)
        if not parts:
            self._after.setText(
                f"<span style='color: {c['ink-faint']}'>"
                + html.escape(tr("settings_preview_none", "No name with this model."))
                + "</span>"
            )
            return
        season = tr("season", "Season")
        folders = [f.replace("{season}", season) for f in example.folders]
        root = self._destination or tr("settings_preview_folder", "Destination")
        path = os.path.join(root, *folders, *parts)
        self._after.setText(_rich(path, c["accent-text"]))

    def retranslate(self) -> None:
        self._label.setText(tr("settings_preview", "Live preview"))
        self._before_lbl.setText(tr("settings_before", "Before"))
        self._after_lbl.setText(tr("settings_after", "After"))
        self._show_texts()

    def _restyle(self) -> None:
        c = _palette(self)
        for label, role in (
            (self._label, "ink-faint"),
            (self._before_lbl, "ink-muted"),
            (self._after_lbl, "ink-muted"),
            (self._before, "ink-faint"),
            (self._after, "ink"),
        ):
            label.setStyleSheet(f"color: {c[role]}; background: transparent;")
        # The window stylesheet replaces the family of setFont.
        for label in (self._before, self._after):
            label.setStyleSheet(
                label.styleSheet() + f" font-family: '{Theme.MONO}'; font-size: 13px;"
            )
        self._show_texts()

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            self._restyle()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        p.fillRect(rect, parse_color(c["bg"]))
        obj = self._stage.object_rect().translated(QPointF(self._stage.pos()))
        if obj.isValid():
            paint_light(p, rect, self._color, obj)
        p.setPen(QPen(parse_color(c["line"]), 1))
        p.drawLine(QPointF(0.5, 0), QPointF(0.5, rect.height()))
        p.end()
