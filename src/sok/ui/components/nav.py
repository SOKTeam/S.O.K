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
from PySide6.QtGui import QFontMetrics, QPainter
from PySide6.QtWidgets import QHBoxLayout, QWidget

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


class NavMark(_Clickable):
    """The "● S.O.K" mark: a coral dot and the name. Opens the home page."""

    DOT = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font = ui_font(15, 700)
        self._font.setLetterSpacing(self._font.SpacingType.AbsoluteSpacing, -0.45)
        self._active = False

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        text = QFontMetrics(self._font).horizontalAdvance("S.O.K")
        return QSize(self.DOT + 9 + text + 1, 30)

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(parse_color(c["accent"]))
        p.drawEllipse(QPointF(self.DOT / 2, self.height() / 2), 4, 4)
        p.setFont(self._font)
        p.setPen(
            parse_color(c["ink"] if self._active or self._hovered else c["ink-muted"])
        )
        p.drawText(
            QRectF(self.DOT + 9, 0, self.width(), self.height()),
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
        layout.addSpacing(40)

        self.words: dict[int, NavWord] = {}
        for i, (index, text) in enumerate(words):
            if i:
                layout.addSpacing(30)
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
