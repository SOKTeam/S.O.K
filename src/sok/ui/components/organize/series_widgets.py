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
"""What the series screen shows of the episodes.

EpisodeLines goes under the selected series of the list: one line per
episode, its code in the accent, its title and what the file was.
EpisodeGrid goes on the scene: a square per episode of a season, filled when
the episode is among the files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from sok.ui.components.base import parse_color
from sok.ui.theme import Theme, ui_font
from sok.ui.tokens import RADIUS


def _palette(widget: QWidget) -> dict[str, str]:
    return getattr(widget.window(), "c", None) or Theme.DARK


@dataclass
class EpisodeLine:
    """An episode under its series: "S01E01", its title, its file."""

    code: str
    title: str
    was: str


class EpisodeLines(QWidget):
    """The episodes of the selected series, under its row.

    The first `limit` episodes are shown, then "+ N other episodes".
    """

    LINE = 46
    INDENT = 14 + 36 + 18

    def __init__(
        self, lines: List[EpisodeLine], was_label: str, more: str, limit: int = 5
    ):
        super().__init__()
        self._lines = lines[:limit]
        self._was_label = was_label
        self._more = more if len(lines) > limit else ""
        height = len(self._lines) * self.LINE + (28 if self._more else 0) + 6
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return QSize(400, self.height())

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        code_font = ui_font(13, 500, mono=True)
        title_font = ui_font(15, 500)
        was_font = ui_font(12, 400, mono=True)
        code_width = QFontMetrics(code_font).horizontalAdvance("S00E00") + 14
        width = self.width() - self.INDENT - code_width - 16
        # A thin line ties the episodes to their series.
        p.setPen(QPen(parse_color(c["line-strong"]), 1))
        p.drawLine(
            self.INDENT - 14, 4, self.INDENT - 14, len(self._lines) * self.LINE - 8
        )
        for i, line in enumerate(self._lines):
            top = i * self.LINE + 4
            p.setFont(code_font)
            p.setPen(parse_color(c["accent-text"]))
            p.drawText(self.INDENT, top + 16, line.code)
            x = self.INDENT + code_width
            p.setFont(title_font)
            p.setPen(parse_color(c["ink"]))
            p.drawText(
                x,
                top + 16,
                QFontMetrics(title_font).elidedText(
                    line.title, Qt.TextElideMode.ElideRight, int(width)
                ),
            )
            p.setFont(was_font)
            p.setPen(parse_color(c["ink-faint"]))
            p.drawText(
                x,
                top + 34,
                QFontMetrics(was_font).elidedText(
                    f"{self._was_label} {line.was}",
                    Qt.TextElideMode.ElideMiddle,
                    int(width),
                ),
            )
        if self._more:
            p.setFont(ui_font(13))
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(self.INDENT, len(self._lines) * self.LINE + 20, self._more)
        p.end()


@dataclass
class SeasonGrid:
    """A season on the scene.

    Attributes:
        title: "Season 1".
        found: "7 episodes found out of 7".
        episodes: Episode numbers of the season, in order.
        present: Episode numbers among the files.
    """

    title: str
    found: str
    episodes: List[int]
    present: List[int]


class EpisodeGrid(QWidget):
    """The seasons of a series on the scene: one square per episode."""

    BOX = QSize(44, 30)
    GAP = 6
    PER_ROW = 7

    def __init__(self, seasons: List[SeasonGrid]):
        super().__init__()
        self._seasons = seasons
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(self._height())

    def _rows(self, season: SeasonGrid) -> int:
        return max(1, -(-len(season.episodes) // self.PER_ROW))

    def _height(self) -> int:
        return sum(
            46 + self._rows(s) * (self.BOX.height() + self.GAP) + 14
            for s in self._seasons
        )

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        heading, muted, box_font = (
            ui_font(17, 600),
            ui_font(14),
            ui_font(12, 500, mono=True),
        )
        y = 0
        for season in self._seasons:
            p.setFont(heading)
            p.setPen(parse_color(c["ink"]))
            p.drawText(0, y + 18, season.title)
            p.setFont(muted)
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(0, y + 38, season.found)
            y += 46
            p.setFont(box_font)
            for i, number in enumerate(season.episodes):
                row, col = divmod(i, self.PER_ROW)
                rect = QRectF(
                    col * (self.BOX.width() + self.GAP) + 0.5,
                    y + row * (self.BOX.height() + self.GAP) + 0.5,
                    self.BOX.width() - 1,
                    self.BOX.height() - 1,
                )
                here = number in season.present
                p.setPen(
                    QPen(
                        parse_color(c["line-strong"] if not here else c["accent-soft"]),
                        1,
                    )
                )
                p.setBrush(
                    parse_color(c["accent-soft"]) if here else Qt.BrushStyle.NoBrush
                )
                p.drawRoundedRect(rect, RADIUS["tag"], RADIUS["tag"])
                p.setPen(parse_color(c["accent-text"] if here else c["ink-faint"]))
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"E{number:02d}")
            y += self._rows(season) * (self.BOX.height() + self.GAP) + 14
        p.end()
