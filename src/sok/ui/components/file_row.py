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

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget

from sok.ui.components.base import parse_color
from sok.ui.components.media_visual import rounded, standin_pixmap
from sok.ui.motion import GAUGE, SORTED, animate
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
        book: Draw the thumbnail as a book: square corners at the spine,
            on the left, with its shadow.
        by_tone: Palette color of the author ("ink-muted" for books).
        phase: Where the item is in a rename: "" (not renaming), "waiting",
            "current", "done", "stays" (left where it is) or "failed".
        state: Short mono text at the right during a rename ("sorted"…).
        line: Second line written instead of "was …" (the new path, or why
            the file did not move), in the palette color line_tone.
        action: Text of a small key drawn at the right ("Pick", "Retry"),
            which emits action_clicked ("" for none).
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
    book: bool = False
    by_tone: str = "ink-faint"
    phase: str = ""
    state: str = ""
    line: str = ""
    line_tone: str = "ink-faint"
    action: str = ""


# Palette color of the state text of each phase of a rename.
PHASE_TONES = {
    "current": "accent-text",
    "stays": "caution",
    "failed": "danger",
}


def draw_check(
    p: QPainter, x: float, center_y: float, color: QColor, progress: float = 1.0
) -> None:
    """The 18px check of a sorted item (Lucide "check", 2px), drawn up to
    progress (0 to 1): the short stroke, then the long one."""
    if progress <= 0:
        return
    pen = QPen(color, 2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    scale = 18 / 24
    points = [
        QPointF(x + 4 * scale, center_y),
        QPointF(x + 9 * scale, center_y + 5 * scale),
        QPointF(x + 20 * scale, center_y - 6 * scale),
    ]
    lengths = [
        ((b.x() - a.x()) ** 2 + (b.y() - a.y()) ** 2) ** 0.5
        for a, b in zip(points, points[1:])
    ]
    left = sum(lengths) * min(1.0, progress)
    path = QPainterPath(points[0])
    for (a, b), length in zip(zip(points, points[1:]), lengths):
        if left <= 0:
            break
        share = min(1.0, left / length)
        path.lineTo(a + (b - a) * share)
        left -= length
    p.drawPath(path)


def draw_small_key(
    p: QPainter, rect: QRectF, text: str, c: dict[str, str], hover: bool = False
) -> None:
    """A small key drawn in a row: the face, its 1px light and shadow."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(parse_color(c["shadow-key-drop"]))
    p.drawRoundedRect(rect.translated(0, 1), RADIUS["key-sm"], RADIUS["key-sm"])
    p.setBrush(parse_color(c["key-hover"] if hover else c["key"]))
    p.drawRoundedRect(rect, RADIUS["key-sm"], RADIUS["key-sm"])
    p.setPen(QPen(parse_color(c["shadow-key-light"]), 1))
    p.drawLine(
        QPointF(rect.left() + RADIUS["key-sm"], rect.top() + 0.5),
        QPointF(rect.right() - RADIUS["key-sm"], rect.top() + 0.5),
    )
    p.setFont(ui_font(13, 600))
    p.setPen(parse_color(c["ink"]))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


def small_key_width(text: str) -> int:
    return QFontMetrics(ui_font(13, 600)).horizontalAdvance(text) + 24


def draw_gauge(
    p: QPainter, x: float, center_y: float, filled: float, c: dict[str, str]
) -> float:
    """Draw the five-notch confidence gauge; return its width.

    Args:
        p: Painter.
        x: Left edge.
        center_y: Vertical center.
        filled: Filled notches, 0 to 5; a fraction lights the next notch
            part of the way (while the gauge fills).
        c: Palette.
    """
    p.setPen(Qt.PenStyle.NoPen)
    off, on = parse_color(c["line-strong"]), parse_color(c["accent"])
    for i in range(NOTCHES):
        share = max(0.0, min(1.0, filled - i))
        color = QColor(
            round(off.red() + (on.red() - off.red()) * share),
            round(off.green() + (on.green() - off.green()) * share),
            round(off.blue() + (on.blue() - off.blue()) * share),
            round(off.alpha() + (on.alpha() - off.alpha()) * share),
        )
        p.setBrush(color)
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


def book_cover(pixmap: QPixmap, width: int, height: int) -> QPixmap:
    """A thumbnail shaped like a book: corners of 3px at the spine (left)
    and 6px at the edge, and the shadow of the spine over 4px."""
    ratio = pixmap.devicePixelRatio() or 1.0
    out = QPixmap(int(width * ratio), int(height * ratio))
    out.setDevicePixelRatio(ratio)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, width, height), 6, 6)
    spine = QPainterPath()
    spine.addRoundedRect(QRectF(0, 0, 12, height), 3, 3)
    path = path.united(spine)
    p.setClipPath(path)
    p.drawPixmap(0, 0, pixmap)
    shadow = QLinearGradient(0, 0, 4, 0)
    shadow.setColorAt(0, QColor(0, 0, 0, 90))
    shadow.setColorAt(1, QColor(0, 0, 0, 0))
    p.fillRect(QRectF(0, 0, 4, height), shadow)
    p.end()
    return out


class FileRow(QWidget):
    """A row of a media list. Click to select it.

    Signals:
        clicked: The row was clicked.
        action_clicked: Its small key (RowData.action) was clicked.
    """

    clicked = Signal()
    action_clicked = Signal()

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
        self._key_rect = QRectF()
        self._key_hover = False
        # Shown values of the gauge and of the sorted check, which move to
        # the data in a short animation (see set_data).
        self._gauge = float(data.confidence)
        self._sorted = 1.0 if data.phase == "done" else 0.0
        self.setMouseTracking(True)
        self.setFixedHeight(self.HEIGHT)
        self.setMinimumWidth(320)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    @property
    def data(self) -> RowData:
        return self._data

    def set_data(self, data: RowData) -> None:
        old = self._data
        self._data = data
        self._thumb = None
        # The gauge fills when the item is recognized.
        if data.confidence > old.confidence and not data.phase:
            animate(self, GAUGE, self._set_gauge, self._gauge, data.confidence)
        else:
            self._gauge = float(data.confidence)
        # The check draws itself and the thumbnail fades when it is sorted.
        if data.phase == "done" and old.phase != "done":
            animate(self, SORTED, self._set_sorted, 0.0, 1.0)
        elif data.phase != "done":
            self._sorted = 0.0
        self.update()

    def _set_gauge(self, value: float) -> None:
        self._gauge = value
        self.update()

    def _set_sorted(self, value: float) -> None:
        self._sorted = value
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
        self._key_hover = False
        self.update()

    def mouseMoveEvent(self, e):  # noqa: N802 - Qt API
        hover = bool(self._data.action) and self._key_rect.contains(e.position())
        if hover != self._key_hover:
            self._key_hover = hover
            self.update()

    def mouseReleaseEvent(self, e):  # noqa: N802 - Qt API
        if e.button() != Qt.MouseButton.LeftButton or not self.rect().contains(
            e.position().toPoint()
        ):
            return
        if self._data.action and self._key_rect.contains(e.position()):
            self.action_clicked.emit()
        else:
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
            if self._data.book:
                self._thumb = book_cover(self._thumb, w, h)
        return self._thumb

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = getattr(self.window(), "c", None) or Theme.DARK
        d = self._data
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect())

        # The item being moved is lit like a selected row.
        lit = self._selected or d.phase == "current"
        if lit or self._hovered:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(parse_color(c["surface-raised"]))
            if not lit:
                p.setOpacity(0.5)
            p.drawRoundedRect(box, RADIUS["key"], RADIUS["key"])
            p.setOpacity(1.0)
            if lit:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(parse_color(c["line"]), 1))
                p.drawRoundedRect(
                    box.adjusted(0.5, 0.5, -0.5, -0.5), RADIUS["key"], RADIUS["key"]
                )

        # Thumbnail with a 1px inner line; faded once sorted.
        tx, ty = self.PAD_X, self.PAD_Y
        if d.phase == "done":
            p.setOpacity(1 - 0.45 * self._sorted)
        p.drawPixmap(tx, ty, self._thumbnail())
        p.setOpacity(1.0)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(parse_color(c["highlight"]), 1))
        thumb_rect = QRectF(
            tx + 0.5, ty + 0.5, self.THUMB.width() - 1, self.THUMB.height() - 1
        )
        path = QPainterPath()
        path.addRoundedRect(thumb_rect, 6, 6)
        p.drawPath(path)

        center_y = self.height() / 2
        right = self.width() - self.PAD_X
        self._key_rect = QRectF()
        if d.phase:
            # During and after a rename: the state, then a key, a check or
            # the gauge; no tags.
            if d.action:
                width = small_key_width(d.action)
                self._key_rect = QRectF(right - width, center_y - 16, width, 32)
                draw_small_key(p, self._key_rect, d.action, c, self._key_hover)
                state_right = self._key_rect.left() - self.GAP
            elif d.phase == "done":
                draw_check(p, right - 18, center_y, parse_color(c["ink"]), self._sorted)
                state_right = right - 28 - self.GAP
            elif d.phase in ("failed",):
                state_right = right
            else:
                gauge_x = right - (NOTCHES * 6 - 3)
                draw_gauge(p, gauge_x, center_y, max(0, min(NOTCHES, self._gauge)), c)
                state_right = gauge_x - self.GAP
            text_right = state_right
            if d.state:
                state_font = ui_font(12, 400, mono=True)
                width = QFontMetrics(state_font).horizontalAdvance(d.state)
                p.setFont(state_font)
                p.setPen(parse_color(c[PHASE_TONES.get(d.phase, "ink-faint")]))
                p.drawText(
                    QRectF(state_right - width, 0, width, self.height()),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                    d.state,
                )
                text_right = state_right - width - self.GAP
        else:
            # Right side: tags then the gauge, measured from the right edge.
            gauge_x = right - (NOTCHES * 6 - 3)
            draw_gauge(p, gauge_x, center_y, max(0, min(NOTCHES, self._gauge)), c)
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
            p.setPen(parse_color(c[d.by_tone]))
            p.drawText(int(x), int(baseline), by)

        if d.line:
            line_font = ui_font(12, 400, mono=True)
            mode = (
                Qt.TextElideMode.ElideRight
                if d.phase == "failed"
                else Qt.TextElideMode.ElideMiddle
            )
            line = QFontMetrics(line_font).elidedText(d.line, mode, int(available))
            p.setFont(line_font)
            p.setPen(parse_color(c[d.line_tone]))
            p.drawText(int(left), int(center_y + 16), line)
        elif d.note:
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


class CoverTile(QWidget):
    """An album in a grid: its square cover, the title and a line under it.

    Same interface as FileRow. Selected, the cover gets a 2px accent ring;
    an unknown album has its title in the caution color.

    Signals:
        clicked: The tile was clicked.
    """

    clicked = Signal()

    RING = 3
    TEXT = 52

    def __init__(self, data: RowData, was_label: str = "was", parent=None):
        super().__init__(parent)
        self._data = data
        self._sorted = 1.0 if data.phase == "done" else 0.0
        self._selected = False
        self._hovered = False
        self._cover: QPixmap | None = None
        self._cover_size = 0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    @property
    def data(self) -> RowData:
        return self._data

    def _set_sorted(self, value: float) -> None:
        self._sorted = value
        self.update()

    def set_data(self, data: RowData) -> None:
        if data.phase == "done" and self._data.phase != "done":
            animate(self, SORTED, self._set_sorted, 0.0, 1.0)
        elif data.phase != "done":
            self._sorted = 0.0
        self._data = data
        self._cover = None
        self.update()

    def set_was_label(self, text: str) -> None:
        """Kept for MediaList: a tile shows no original name."""

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def is_selected(self) -> bool:
        return self._selected

    def height_for(self, width: int) -> int:
        """Height of a tile of this width: the cover, then two lines."""
        return width + self.TEXT

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

    def _cover_pixmap(self, size: int) -> QPixmap:
        if self._cover is None or self._cover_size != size:
            ratio = self.devicePixelRatioF()
            source = self._data.thumbnail or standin_pixmap(
                self._data.title, "", size, size, ratio, text=False
            )
            self._cover = rounded(source, size, size, 10)
            self._cover_size = size
        return self._cover

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = getattr(self.window(), "c", None) or Theme.DARK
        d = self._data
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ring = self.RING
        size = max(1, self.width() - 2 * ring)
        cover = QRectF(ring, ring, size, size)
        if d.phase == "done":
            p.setOpacity(1 - 0.45 * self._sorted)
        p.drawPixmap(int(ring), int(ring), self._cover_pixmap(size))
        p.setOpacity(1.0)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(parse_color(c["highlight"]), 1))
        p.drawRoundedRect(cover.adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)
        if d.phase == "current":
            p.setPen(QPen(parse_color(c["accent"]), 2))
            p.drawRoundedRect(cover.adjusted(-2, -2, 2, 2), 12, 12)
        elif self._selected or self.hasFocus():
            p.setPen(QPen(parse_color(c["accent"]), 2))
            p.drawRoundedRect(cover.adjusted(-2, -2, 2, 2), 12, 12)
        elif self._hovered:
            p.setPen(QPen(parse_color(c["line-strong"]), 2))
            p.drawRoundedRect(cover.adjusted(-2, -2, 2, 2), 12, 12)

        top = ring + size + 10
        title_font = ui_font(15, 600)
        title_font.setLetterSpacing(title_font.SpacingType.AbsoluteSpacing, -0.22)
        p.setFont(title_font)
        p.setPen(parse_color(c["caution"] if d.unknown else c["ink"]))
        p.drawText(
            int(ring),
            int(top + 15),
            QFontMetrics(title_font).elidedText(
                d.title, Qt.TextElideMode.ElideRight, int(size)
            ),
        )
        if d.phase == "done":
            draw_check(
                p,
                cover.right() - 26,
                cover.top() + 18,
                parse_color(c["ink"]),
                self._sorted,
            )
        # During a rename, the state replaces the artist.
        line = d.state if d.phase else (d.note or d.by)
        if line:
            note_font = ui_font(13)
            p.setFont(note_font)
            p.setPen(
                parse_color(
                    c[PHASE_TONES.get(d.phase, "ink-faint")]
                    if d.phase
                    else c["ink-muted"]
                )
            )
            p.drawText(
                int(ring),
                int(top + 34),
                QFontMetrics(note_font).elidedText(
                    line, Qt.TextElideMode.ElideRight, int(size)
                ),
            )
        p.end()
