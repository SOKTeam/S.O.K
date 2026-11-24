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
"""Pieces of the empty screen of a media page (mockup 05).

Three empty places fanned out above the title, in the shape of the items of
the page (posters, covers or books), and the tags of what S.O.K recognizes
(the consoles, or the accepted formats) under the keys.
"""

from __future__ import annotations

from typing import List

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from sok.ui.components.base import parse_color
from sok.ui.components.file_row import draw_tag
from sok.ui.components.scene import Shape, _soft_shadow
from sok.ui.theme import Theme, ui_font

# Size of a place, by shape of the items of the page.
PLACE_SIZES = {
    Shape.POSTER: QSize(100, 150),
    Shape.COVER: QSize(120, 120),
    Shape.BOOK: QSize(100, 150),
}


def _palette(widget: QWidget) -> dict[str, str]:
    return getattr(widget.window(), "c", None) or Theme.DARK


class EmptyFan(QWidget):
    """Three empty places, the outer ones tilted and lower (CSS: rotate
    ±8°, translateY 14px), each with its 1px edge, its light and its
    shadow."""

    GAP = 14
    TILT = 8
    DROP = 14

    def __init__(self, shape: Shape = Shape.POSTER, parent=None):
        super().__init__(parent)
        self._shape = shape
        size = PLACE_SIZES[shape]
        self.setFixedSize(3 * size.width() + 2 * self.GAP + 60, size.height() + 70)

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        size = PLACE_SIZES[self._shape]
        w, h = size.width(), size.height()
        radius = 6 if self._shape == Shape.BOOK else 16
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        center_x = self.width() / 2
        shadow = _soft_shadow(size, radius, parse_color(c["shadow-poster-drop"]))
        # The outer places first, so the middle one is on top.
        for offset, tilt, drop in (
            (-(w + self.GAP), -self.TILT, self.DROP),
            (w + self.GAP, self.TILT, self.DROP),
            (0, 0, 0),
        ):
            p.save()
            p.translate(center_x + offset, 20 + drop + h / 2)
            p.rotate(tilt)
            rect = QRectF(-w / 2, -h / 2, w, h)
            # Shadow below (CSS: 0 20px 40px).
            p.drawImage(rect.topLeft() + QPointF(-80, 20 - 80), shadow)
            path = QPainterPath()
            path.addRoundedRect(rect, radius, radius)
            face = QLinearGradient(rect.topLeft(), rect.bottomRight())
            face.setColorAt(0, parse_color(c["key"]))
            face.setColorAt(1, parse_color(c["surface"]))
            p.fillPath(path, face)
            p.setPen(QPen(parse_color(c["line"]), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
            p.setPen(QPen(parse_color(c["highlight"]), 1))
            p.drawLine(
                QPointF(rect.left() + radius, rect.top() + 1.5),
                QPointF(rect.right() - radius, rect.top() + 1.5),
            )
            p.restore()
        p.end()


class TagCloud(QWidget):
    """Tags in Geist Mono, centered on lines of at most max_width."""

    GAP = 6
    LINE = 24

    def __init__(self, max_width: int = 560, parent=None):
        super().__init__(parent)
        self._tags: List[str] = []
        self._max_width = max_width
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def set_tags(self, tags: List[str]) -> None:
        self._tags = list(tags)
        self.updateGeometry()
        self.setFixedHeight(len(self._lines(self._max_width)) * self.LINE)
        self.update()

    @staticmethod
    def _width(tag: str) -> int:
        return QFontMetrics(ui_font(11, 400, mono=True)).horizontalAdvance(tag) + 12

    def _lines(self, width: int) -> List[List[str]]:
        lines: List[List[str]] = []
        used = 0
        for tag in self._tags:
            tag_w = self._width(tag)
            if lines and used + self.GAP + tag_w <= width:
                lines[-1].append(tag)
                used += self.GAP + tag_w
            else:
                lines.append([tag])
                used = tag_w
        return lines

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return QSize(self._max_width, len(self._lines(self._max_width)) * self.LINE)

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = min(self.width(), self._max_width)
        for row, line in enumerate(self._lines(width)):
            line_w = sum(self._width(t) for t in line) + self.GAP * (len(line) - 1)
            x = (self.width() - line_w) / 2
            for tag in line:
                draw_tag(p, x, row * self.LINE + self.LINE / 2, tag, c)
                x += self._width(tag) + self.GAP
        p.end()
