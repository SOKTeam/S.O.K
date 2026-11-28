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
"""The tracks of an album on the scene: number, title and length."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QFontMetrics, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from sok.ui.components.base import parse_color
from sok.ui.theme import Theme, ui_font


@dataclass
class TrackLine:
    """A track: "01", its title, its length ("5:20", or "")."""

    number: str
    title: str
    length: str = ""


class TrackList(QWidget):
    """The first tracks of an album, then "+ N tracks"."""

    LINE = 28

    def __init__(self, lines: List[TrackLine], more: str = "", limit: int = 6):
        super().__init__()
        self._lines = lines[:limit]
        self._more = more if len(lines) > limit else ""
        self.setFixedHeight(len(self._lines) * self.LINE + (26 if self._more else 0))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return QSize(360, self.height())

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = getattr(self.window(), "c", None) or Theme.DARK
        p = QPainter(self)
        mono, title_font = ui_font(13, 400, mono=True, tabular=True), ui_font(15)
        number_width = QFontMetrics(mono).horizontalAdvance("00") + 16
        for i, line in enumerate(self._lines):
            top = i * self.LINE
            length_width = QFontMetrics(mono).horizontalAdvance(line.length)
            p.setFont(mono)
            p.setPen(parse_color(c["ink-faint"]))
            p.drawText(
                QRectF(0, top, number_width, self.LINE),
                Qt.AlignmentFlag.AlignVCenter,
                line.number,
            )
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(
                QRectF(self.width() - length_width, top, length_width, self.LINE),
                Qt.AlignmentFlag.AlignVCenter,
                line.length,
            )
            p.setFont(title_font)
            p.setPen(parse_color(c["ink"]))
            width = self.width() - number_width - length_width - 16
            p.drawText(
                QRectF(number_width, top, width, self.LINE),
                Qt.AlignmentFlag.AlignVCenter,
                QFontMetrics(title_font).elidedText(
                    line.title, Qt.TextElideMode.ElideRight, int(width)
                ),
            )
        if self._more:
            p.setFont(ui_font(13))
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(0, len(self._lines) * self.LINE + 18, self._more)
        p.end()
