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
"""
The row of a list: what S.O.K found, and below it what the file "was".

Thumbnail, clean title in large type with its year and its author, then
"was <original name>" in Geist Mono: the before/after of S.O.K, seen without
waiting. At the right, quality tags drawn as outlines and the five-notch
confidence gauge.
"""

from dataclasses import dataclass, field

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from sok.ui.components.base import parse_color
from sok.ui.components.media_visual import rounded, standin_pixmap
from sok.ui.theme import Theme, ui_font
from sok.ui.tokens import RADIUS

NOTCHES = 5


@dataclass
class RowData:
    """What a FileRow shows.

    Attributes:
        title: Clean title found by S.O.K, or the text shown when unknown.
        was: Original file name, shown after the translated "was".
        year: Year, in Geist Mono ("" for none).
        by: Director, author or artist ("" for none).
        tags: Quality tags ("4K", "Atmos"…).
        confidence: Filled notches, 0 to 5.
        unknown: Not recognized: the title is written in the caution color.
        thumbnail: Poster or cover; None draws the stand-in.
        note: Second line written instead of "was <original name>", such as
            "Season 1 · 7 episodes" for a series ("" for none).
    """

    title: str
    was: str = ""
    year: str = ""
    by: str = ""
    tags: list[str] = field(default_factory=list)
    confidence: int = 0
    unknown: bool = False
    thumbnail: QPixmap | None = None
    note: str = ""


def draw_gauge(
    p: QPainter, x: float, center_y: float, filled: int, c: dict[str, str]
) -> float:
    """Draw the five-notch confidence gauge; return its width.

    Args:
        p: Painter.
        x: Left edge.
        center_y: Vertical center.
        filled: Filled notches, 0 to 5.
        c: Palette.
    """
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(NOTCHES):
        p.setBrush(parse_color(c["accent"] if i < filled else c["line-strong"]))
        p.drawRoundedRect(QRectF(x + i * 6, center_y - 7, 3, 14), 1.5, 1.5)
    return NOTCHES * 6 - 3


def draw_tag(
    p: QPainter, x: float, center_y: float, text: str, c: dict[str, str]
) -> float:
    """Draw a quality tag as an outline; return its width."""
    font = ui_font(11, 400, mono=True)
    width = QFontMetrics(font).horizontalAdvance(text) + 12
    rect = QRectF(x + 0.5, center_y - 8.5, width - 1, 17)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(parse_color(c["line-strong"]), 1))
    p.drawRoundedRect(rect, RADIUS["tag"], RADIUS["tag"])
    p.setFont(font)
    p.setPen(parse_color(c["ink-muted"]))
    p.drawText(QRectF(x, center_y - 9, width, 18), Qt.AlignmentFlag.AlignCenter, text)
    return width


class FileRow(QWidget):
    """A row of a media list. Click to select it.

    Signals:
        clicked: The row was clicked.
    """

    clicked = Signal()

    THUMB = QSize(36, 54)
    PAD_X, PAD_Y, GAP = 14, 10, 18
    HEIGHT = 54 + 2 * 10

    def __init__(self, data: RowData, was_label: str = "was", parent=None):
        """Build the row.

        Args:
            data: What the row shows.
            was_label: Translated word written before the original name.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._data = data
        self._was_label = was_label
        self._selected = False
        self._hovered = False
        self._thumb: QPixmap | None = None
        self.setFixedHeight(self.HEIGHT)
        self.setMinimumWidth(320)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    @property
    def data(self) -> RowData:
        return self._data

    def set_data(self, data: RowData) -> None:
        self._data = data
        self._thumb = None
        self.update()

    def set_was_label(self, text: str) -> None:
        self._was_label = text
        self.update()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def is_selected(self) -> bool:
        return self._selected

    def enterEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = True
        self.update()

    def leaveEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = False
        self.update()

    def mouseReleaseEvent(self, e):  # noqa: N802 - Qt API
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            e.position().toPoint()
        ):
            self.clicked.emit()

    def keyPressEvent(self, e):  # noqa: N802 - Qt API
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(e)

    def _thumbnail(self) -> QPixmap:
        if self._thumb is None:
            w, h = self.THUMB.width(), self.THUMB.height()
            ratio = self.devicePixelRatioF()
            source = self._data.thumbnail or standin_pixmap(
                self._data.title, "", w, h, ratio
            )
            self._thumb = rounded(source, w, h, 6)
        return self._thumb

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = getattr(self.window(), "c", None) or Theme.DARK
        d = self._data
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect())

        if self._selected or self._hovered:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(parse_color(c["surface-raised"]))
            if not self._selected:
                p.setOpacity(0.5)
            p.drawRoundedRect(box, RADIUS["key"], RADIUS["key"])
            p.setOpacity(1.0)
            if self._selected:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(parse_color(c["line"]), 1))
                p.drawRoundedRect(
                    box.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS["key"], RADIUS["key"]
                )

        # Thumbnail with a 1px inner line.
        tx, ty = self.PAD_X, self.PAD_Y
        p.drawPixmap(tx, ty, self._thumbnail())
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(parse_color(c["highlight"]), 1))
        thumb_rect = QRectF(
            tx + 0.5, ty + 0.5, self.THUMB.width() - 1, self.THUMB.height() - 1
        )
        path = QPainterPath()
        path.addRoundedRect(thumb_rect, 6, 6)
        p.drawPath(path)

        # Right side: tags then the gauge, measured from the right edge.
        center_y = self.height() / 2
        right = self.width() - self.PAD_X
        gauge_x = right - (NOTCHES * 6 - 3)
        draw_gauge(p, gauge_x, center_y, max(0, min(NOTCHES, d.confidence)), c)
        x = gauge_x - self.GAP
        tag_widths = [
            QFontMetrics(ui_font(11, 400, mono=True)).horizontalAdvance(t) + 12
            for t in d.tags
        ]
        tags_width = sum(tag_widths) + 6 * max(0, len(d.tags) - 1)
        x -= tags_width
        tags_left = x
        for tag, width in zip(d.tags, tag_widths):
            draw_tag(p, x, center_y, tag, c)
            x += width + 6
        text_right = (tags_left if d.tags else gauge_x) - self.GAP

        # Title line: title, year, author, on one baseline.
        left = tx + self.THUMB.width() + self.GAP
        title_font = ui_font(17, 600)
        title_font.setLetterSpacing(title_font.SpacingType.AbsoluteSpacing, -0.34)
        year_font = ui_font(13, 400, mono=True)
        by_font = ui_font(14)
        baseline = center_y - 3
        available = max(0, text_right - left)

        fm = QFontMetrics(title_font)
        title = fm.elidedText(d.title, Qt.TextElideMode.ElideRight, int(available))
        p.setFont(title_font)
        p.setPen(parse_color(c["caution"] if d.unknown else c["ink"]))
        p.drawText(int(left), int(baseline), title)
        x = left + fm.horizontalAdvance(title) + 10
        if d.year and x < text_right:
            p.setFont(year_font)
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(int(x), int(baseline), d.year)
            x += QFontMetrics(year_font).horizontalAdvance(d.year) + 10
        if d.by and x < text_right:
            by = QFontMetrics(by_font).elidedText(
                d.by, Qt.TextElideMode.ElideRight, int(text_right - x)
            )
            p.setFont(by_font)
            p.setPen(parse_color(c["ink-faint"]))
            p.drawText(int(x), int(baseline), by)

        if d.note:
            note_font = ui_font(14)
            note = QFontMetrics(note_font).elidedText(
                d.note, Qt.TextElideMode.ElideRight, int(available)
            )
            p.setFont(note_font)
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(int(left), int(center_y + 16), note)
        elif d.was:
            was_font = ui_font(12, 400, mono=True)
            was = QFontMetrics(was_font).elidedText(
                f"{self._was_label} {d.was}",
                Qt.TextElideMode.ElideMiddle,
                int(available),
            )
            p.setFont(was_font)
            p.setPen(parse_color(c["ink-faint"]))
            p.drawText(int(left), int(center_y + 16), was)

        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(parse_color(c["accent"]), 2))
            p.drawRoundedRect(box.adjusted(1, 1, -1, -1), RADIUS["key"], RADIUS["key"])
        p.end()
