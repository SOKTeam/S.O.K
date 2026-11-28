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
Typographic navigation of the art direction.

The media types are big words with the number of items to sort written as a
superscript, in a row at the top of the window: no tabs, no sidebar, no
background. The "● S.O.K" mark at the left opens the home page; History and
Settings are icons at the right, outside the navigation.
"""

from functools import partial

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QSpacerItem, QWidget

from sok.ui.components.base import parse_color
from sok.ui.theme import Theme, svg_icon, ui_font
from sok.ui.tokens import SPACE


def _palette(widget: QWidget) -> dict[str, str]:
    """Return the palette of the widget's window."""
    return getattr(widget.window(), "c", None) or Theme.DARK


class _Clickable(QWidget):
    """A widget that emits clicked on a left click and shows a hand cursor."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    def enterEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = True
        self.update()

    def leaveEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = False
        self.update()

    def mousePressEvent(self, e):  # noqa: N802 - Qt API
        # Taken here: left to the window, the press in the navigation row
        # would start moving it (Linux), and the click would never end here.
        if e.button() == Qt.MouseButton.LeftButton:
            e.accept()
        else:
            super().mousePressEvent(e)

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


class NavWord(_Clickable):
    """A media type in the navigation: a word and its count as a superscript.

    Active, the word is ink and its count the accent; otherwise both are
    ink-faint, ink-muted under the mouse.
    """

    GAP = SPACE["1"]

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._text = text
        self._count: int | None = None
        self._active = False
        self._word_font = ui_font(26, 600)
        self._word_font.setLetterSpacing(
            self._word_font.SpacingType.AbsoluteSpacing, -0.035 * 26
        )
        self._count_font = ui_font(11, 500, mono=True)

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:  # noqa: N802 - Qt API
        self._text = text
        self.updateGeometry()
        self.update()

    def set_count(self, count: int | None) -> None:
        """Show the number of items to sort, or nothing with None."""
        self._count = count
        self.updateGeometry()
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def is_active(self) -> bool:
        return self._active

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        width = QFontMetrics(self._word_font).horizontalAdvance(self._text)
        if self._count is not None:
            width += self.GAP + QFontMetrics(self._count_font).horizontalAdvance(
                str(self._count)
            )
        return QSize(width + 1, 30)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return self.sizeHint()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        if self._active:
            word, count = c["ink"], c["accent-text"]
        else:
            word = c["ink-muted"] if self._hovered else c["ink-faint"]
            count = word
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setFont(self._word_font)
        p.setPen(parse_color(word))
        width = QFontMetrics(self._word_font).horizontalAdvance(self._text)
        p.drawText(
            QRectF(0, 0, width + 1, 30),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._text,
        )
        if self._count is not None:
            # Top of the superscript 2px below the top of the line box.
            p.setFont(self._count_font)
            p.setPen(parse_color(count))
            p.drawText(
                QRectF(width + self.GAP, 2, 60, 14),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                str(self._count),
            )
        p.end()


# The cube of the S.O.K logo, as strokes in its 512 × 508 box: the outline
# and the top face (open at the left corner), then the front vertical edge
# (not touching the center), which is drawn in the accent.
CUBE_OUTLINE = [
    (124, 121),
    (256, 62),
    (442, 146),
    (256, 229),
    (70, 146),
    (70, 360),
    (256, 446),
    (442, 360),
    (442, 146),
]
CUBE_EDGE = [(256, 284), (256, 446)]
CUBE_STROKE = 40


def draw_cube(p: QPainter, rect: QRectF, ink: QColor, accent: QColor) -> None:
    """The S.O.K cube in rect: ink strokes, its front edge in the accent."""
    scale = min(rect.width() / 512, rect.height() / 508)
    x0 = rect.x() + (rect.width() - 512 * scale) / 2
    y0 = rect.y() + (rect.height() - 508 * scale) / 2

    def path(points) -> QPainterPath:
        result = QPainterPath(
            QPointF(x0 + points[0][0] * scale, y0 + points[0][1] * scale)
        )
        for x, y in points[1:]:
            result.lineTo(QPointF(x0 + x * scale, y0 + y * scale))
        return result

    p.setBrush(Qt.BrushStyle.NoBrush)
    for points, color in ((CUBE_OUTLINE, ink), (CUBE_EDGE, accent)):
        pen = QPen(color, CUBE_STROKE * scale)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPath(path(points))


class NavMark(_Clickable):
    """The mark: the S.O.K cube (its front edge in the accent) and the name.
    Opens the home page, and is written in ink while it is open."""

    CUBE = 22
    GAP = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font = ui_font(20, 700)
        self._font.setLetterSpacing(self._font.SpacingType.AbsoluteSpacing, -0.7)
        self._active = False

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        text = QFontMetrics(self._font).horizontalAdvance("S.O.K")
        return QSize(self.CUBE + self.GAP + text + 1, 30)

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        ink = parse_color(c["ink"] if self._active or self._hovered else c["ink-muted"])
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        top = (self.height() - self.CUBE) / 2
        draw_cube(
            p, QRectF(0, top, self.CUBE, self.CUBE), ink, parse_color(c["accent"])
        )
        p.setFont(self._font)
        p.setPen(ink)
        p.drawText(
            QRectF(self.CUBE + self.GAP, 0, self.width(), self.height()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "S.O.K",
        )
        p.end()


class NavIcon(_Clickable):
    """An icon at the right of the navigation (History, Settings)."""

    SIZE = 36

    def __init__(self, icon: str, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._active = False
        self.setFixedSize(self.SIZE, self.SIZE)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        color = c["ink"] if self._active or self._hovered else c["ink-muted"]
        pixmap = svg_icon(self._icon, color, 18)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._active or self._hovered:
            # A light key behind the icon of the page open, as on hover.
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(parse_color(c["surface-raised"]))
            p.drawRoundedRect(QRectF(self.rect()), 10, 10)
        offset = (self.SIZE - 18) // 2
        p.drawPixmap(offset, offset, pixmap)
        p.end()


class NavBar(QWidget):
    """The navigation row at the top of the window.

    Signals:
        navigate(int): Index of the page to show.
    """

    navigate = Signal(int)

    def __init__(
        self,
        home: int,
        words: list[tuple[int, str]],
        icons: list[tuple[int, str]],
        parent=None,
    ):
        """Build the row.

        Args:
            home: Page opened by the "● S.O.K" mark.
            words: (page index, text) of each media type, in order.
            icons: (page index, icon name) of each icon at the right.
        """
        super().__init__(parent)
        self.setObjectName("NavBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE["8"], SPACE["4"], SPACE["6"], SPACE["4"])
        layout.setSpacing(0)

        self._items: dict[int, NavWord | NavMark | NavIcon] = {}
        self.mark = NavMark()
        self._connect(self.mark, home)
        layout.addWidget(self.mark)
        # The gaps after the mark and between the words narrow with the
        # window (fit()).
        self._gaps: list[tuple[QSpacerItem, int, int]] = []
        self._add_gap(layout, *self.MARK_GAP)

        self.words: dict[int, NavWord] = {}
        for i, (index, text) in enumerate(words):
            if i:
                self._add_gap(layout, *self.WORD_GAP)
            word = NavWord(text)
            self.words[index] = word
            self._connect(word, index)
            layout.addWidget(word)
        layout.addStretch()

        self.icons: dict[int, NavIcon] = {}
        for index, name in icons:
            icon = NavIcon(name)
            self.icons[index] = icon
            self._connect(icon, index)
            layout.addWidget(icon)

    # (narrowest, widest) gap, in px, after the mark and between two words.
    MARK_GAP = (24, 40)
    WORD_GAP = (18, 30)

    def _add_gap(self, layout: QHBoxLayout, low: int, high: int) -> None:
        gap = QSpacerItem(high, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        layout.addItem(gap)
        self._gaps.append((gap, low, high))

    def fit(self, width: int) -> None:
        """Narrow the gaps between the words in a narrow window, from 1200px
        down to 850px, following the width without a jump."""
        share = min(1.0, max(0.0, (width - 850) / 350))
        changed = False
        for gap, low, high in self._gaps:
            size = round(low + (high - low) * share)
            if gap.sizeHint().width() != size:
                gap.changeSize(
                    size, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
                )
                changed = True
        layout = self.layout()
        if changed and layout is not None:
            layout.invalidate()

    def _connect(self, item, index: int) -> None:
        self._items[index] = item
        item.clicked.connect(partial(self.navigate.emit, index))

    def set_current(self, index: int) -> None:
        """Show which page is open."""
        for i, item in self._items.items():
            item.set_active(i == index)

    def set_count(self, index: int, count: int | None) -> None:
        """Set the superscript of a media type (None hides it)."""
        if index in self.words:
            self.words[index].set_count(count)
