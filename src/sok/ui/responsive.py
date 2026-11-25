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
"""Sizes that follow the size of the window.

The pages call these from their resizeEvent: the right column (scene,
preview, summary) takes about a third of the page, the big titles get
smaller in a narrow window, and the content of the window stops growing past
MAX_CONTENT_WIDTH, centered (see CenteredColumn).
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    QVariantAnimation,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import QBoxLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from sok.ui.components.base import KeyButton, parse_color
from sok.ui.motion import DOCK, SLIDE_IN, SLIDE_OUT, animate
from sok.ui.theme import ui_font

# Widest the navigation and the pages get; past it they are centered.
MAX_CONTENT_WIDTH = 1760

# The right column: about 36% of the page, from 320 to 520px (the mockups
# give it 420 to 520).
SIDE_SHARE = 0.36
SIDE_MIN, SIDE_MAX = 320, 520

# Narrowest page that shows its right column beside the list; below, the
# column slides out to the right and opens over the list (SidePanel). It
# comes back beside the list only past NARROW_WIDTH + NARROW_MARGIN, so that
# it does not go back and forth while the window is resized near the limit.
NARROW_WIDTH = 1000
NARROW_MARGIN = 40

# Height around which the decorations of a screen (the empty places of the
# empty screen, the covers of the summary) leave room for the text. They
# shrink and fade out over FADE_BAND px around it, following the window.
LOW_HEIGHT = 620
FADE_BAND = 100


def presence(value: int, threshold: int) -> float:
    """How much of a decoration shows for this height: 1 from FADE_BAND / 2
    above threshold, 0 from FADE_BAND / 2 under it, in between linearly."""
    return min(1.0, max(0.0, (value - threshold) / FADE_BAND + 0.5))


def side_width(page_width: int) -> int:
    """Width of the right column of a page this wide."""
    return max(SIDE_MIN, min(SIDE_MAX, round(page_width * SIDE_SHARE)))


def display_px(page_width: int) -> int:
    """Size of the big title of a page this wide: 52px from 1180px, 40px
    at 900px and under, following the width pixel by pixel in between (no
    jump while the window is resized)."""
    t = min(1.0, max(0.0, (page_width - 900) / 280))
    return round(40 + 12 * t)


def display_font(page_width: int) -> QFont:
    """The big title font (weight 650, tracking -0.04em) for a page width."""
    px = display_px(page_width)
    font = ui_font(px, 650)
    font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, -0.04 * px)
    return font


def fit_display(labels: list[QLabel], page_width: int) -> None:
    """Give these big titles the size of the page width."""
    px = display_px(page_width)
    for label in labels:
        if label.font().pixelSize() != px:
            label.setFont(display_font(page_width))


class CenteredColumn(QWidget):
    """Holds one widget, as wide as the window up to MAX_CONTENT_WIDTH, then
    centered with empty margins on both sides."""

    def __init__(self, child: QWidget, parent=None):
        super().__init__(parent)
        self._child = child
        child.setParent(self)

    def resizeEvent(self, e):  # noqa: N802 - Qt API
        super().resizeEvent(e)
        width = min(self.width(), MAX_CONTENT_WIDTH)
        self._child.setGeometry((self.width() - width) // 2, 0, width, self.height())

    def sizeHint(self):  # noqa: N802 - Qt API
        return self._child.sizeHint()

    def minimumSizeHint(self):  # noqa: N802 - Qt API
        return self._child.minimumSizeHint()


class _Dim(QWidget):
    """The shade over the list while the panel is open; a click closes it."""

    def __init__(self, on_click: Callable[[], None], parent: QWidget):
        super().__init__(parent)
        self._on_click = on_click
        self.hide()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 115))
        p.end()

    def mousePressEvent(self, e):  # noqa: N802 - Qt API
        self._on_click()


class _Holder(QWidget):
    """The right column and, over a narrow page, its key back to the list."""

    def __init__(self, side: QWidget, back, parent=None):
        super().__init__(parent)
        self.setObjectName("SidePanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.back_row = QWidget()
        row = QHBoxLayout(self.back_row)
        row.setContentsMargins(20, 14, 20, 0)
        row.addWidget(back)
        row.addStretch()
        self.back_row.hide()
        layout.addWidget(self.back_row)
        layout.addWidget(side, 1)
        # Painted only over the list; beside it the window shows through.
        self.opaque = False

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = getattr(self.window(), "c", None)
        p = QPainter(self)
        if c and self.opaque:
            p.fillRect(self.rect(), parse_color(c["bg"]))
        p.end()


class SidePanel(QObject):
    """The right column of a page: beside the list in a wide page, over it
    in a narrow one (under NARROW_WIDTH), where open() slides it in from
    the right and its "← List" key, Esc or a click on the list close it.

    When the page gets narrow, the column slides out to the right while the
    list widens into its place; when it gets wide again, it slides back in.

    Args:
        host: The screen holding the list and the column.
        layout: The layout of the host the column is added to (last, with
            no margin at the right).
        side: The column (scene, pick panel, summary…).
        back_text: Gives the translated text of the key back to the list.
    """

    # The column moved (for the light the window paints under it).
    moved = Signal()

    def __init__(
        self,
        host: QWidget,
        layout: QBoxLayout,
        side: QWidget,
        back_text: Callable[[], str],
    ):
        super().__init__(host)
        self._host = host
        self._layout = layout
        self._side = side
        self._back_text = back_text
        self._back = KeyButton("", small=True)
        self._back.clicked.connect(self.close)
        self.holder = _Holder(side, self._back)
        layout.addWidget(self.holder)
        # Takes the place of the column in the layout while it moves, so
        # that the list widens or narrows with it.
        self._gap = QWidget()
        self._gap.hide()
        self._dim = _Dim(self.close, host)
        self._narrow = False
        self._open = False
        self._page_width = 0
        self._slide: Optional[QPropertyAnimation] = None
        # The column going out or coming back, and what ends that move.
        self._move: Optional[QVariantAnimation] = None
        self._end_move: Optional[Callable[[], None]] = None
        # Width of the column while it goes out (it keeps its width).
        self._leaving_width = 0
        escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), host)
        escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        escape.activated.connect(self.close)
        host.installEventFilter(self)
        self.retranslate()

    def retranslate(self) -> None:
        self._back.setText("← " + self._back_text())

    @property
    def narrow(self) -> bool:
        return self._narrow

    def is_open(self) -> bool:
        return self._narrow and self._open

    def column_width(self, page_width: int) -> int:
        """Width of the column: a third of a wide page, most of a narrow one."""
        if self._leaving_width:
            return self._leaving_width
        if self._narrow:
            return max(SIDE_MIN, min(560, round(page_width * 0.62)))
        return side_width(page_width)

    def fit(self, page_width: int) -> None:
        """Beside the list or over it, from the width of the page."""
        self._page_width = page_width
        limit = NARROW_WIDTH + (NARROW_MARGIN if self._narrow else 0)
        narrow = page_width < limit
        if narrow != self._narrow:
            if self._host.isVisible():
                self._go_out() if narrow else self._come_back()
            else:
                self._set_narrow(narrow)
        self._place()

    def _set_narrow(self, narrow: bool) -> None:
        """Beside the list or out of it, at once."""
        self._finish_move()
        self._narrow = narrow
        self._open = False
        self._dim.hide()
        if narrow:
            self._layout.removeWidget(self.holder)
            self.holder.setParent(self._host)
            self.holder.hide()
        else:
            self.holder.setParent(None)
            self._layout.addWidget(self.holder)
            self.holder.show()
        self.holder.back_row.setVisible(narrow)
        self.holder.opaque = narrow

    def _finish_move(self) -> None:
        """End the move in progress at once, at its end."""
        if self._slide is not None:
            self._slide.stop()
            self._slide = None
        if self._move is not None:
            self._move.stop()
            self._move = None
        if self._end_move is not None:
            end, self._end_move = self._end_move, None
            end()

    def _swap(self, out: QWidget, into: QWidget) -> None:
        """Put into in the layout at the place of out."""
        index = self._layout.indexOf(out)
        self._layout.removeWidget(out)
        self._layout.insertWidget(index, into)

    def _go_out(self) -> None:
        """The column slides out to the right; the list widens into its
        place."""
        self._finish_move()
        self._narrow = True
        self._open = False
        width = self.holder.width()
        self._leaving_width = width
        self._gap.setFixedWidth(width)
        self._swap(self.holder, self._gap)
        self._gap.show()
        self.holder.setParent(self._host)
        self.holder.setGeometry(
            self._host.width() - width, 0, width, self._host.height()
        )
        self.holder.show()
        self.holder.raise_()

        def step(t: float) -> None:
            self._gap.setFixedWidth(round(width * (1 - t)))
            # Laid out now, not at the next turn: the list and the column
            # move together.
            self._layout.activate()
            self.holder.move(round(self._host.width() - width * (1 - t)), 0)
            self.moved.emit()

        def end() -> None:
            self._layout.removeWidget(self._gap)
            self._gap.hide()
            self._leaving_width = 0
            self.holder.hide()
            self.holder.back_row.show()
            self.holder.opaque = True
            self._side.setFixedWidth(self.column_width(self._page_width))
            self._place()
            self.moved.emit()

        self._start_move(step, end)

    def _come_back(self) -> None:
        """The column slides back in from the right, beside the list."""
        self._finish_move()
        self._narrow = False
        self._open = False
        self._dim.hide()
        width = side_width(self._page_width)
        self._side.setFixedWidth(width)
        self.holder.back_row.hide()
        self.holder.opaque = False
        # From where it is: out of the page, or open over the list.
        start = self._host.width() - (
            self.holder.x() if self.holder.isVisible() else self._host.width()
        )
        start = max(0, start)
        self.holder.resize(width, self._host.height())
        self._gap.setFixedWidth(0)
        self._layout.addWidget(self._gap)
        self._gap.show()
        self.holder.show()
        self.holder.raise_()

        def step(t: float) -> None:
            shown = start + (width - start) * t
            self._gap.setFixedWidth(round(width * t))
            # Laid out now, not at the next turn: the list and the column
            # move together.
            self._layout.activate()
            self.holder.move(round(self._host.width() - shown), 0)
            self.moved.emit()

        def end() -> None:
            self._swap(self._gap, self.holder)
            self._gap.hide()
            self.holder.show()
            self.moved.emit()

        self._start_move(step, end)

    def _start_move(
        self, step: Callable[[float], None], end: Callable[[], None]
    ) -> None:
        self._end_move = end

        def done() -> None:
            self._move = None
            self._finish_move()

        self._move = animate(self.holder, DOCK, step, on_done=done)

    def _target(self) -> QPoint:
        return QPoint(self._host.width() - self.holder.width(), 0)

    def _place(self) -> None:
        if not self._narrow or self._move is not None:
            return
        width = self.column_width(self._host.width())
        self.holder.resize(width, self._host.height())
        self.holder.move(
            self._target() if self._open else QPoint(self._host.width(), 0)
        )
        self._dim.setGeometry(self._host.rect())

    def open(self) -> None:
        """Slide the column over the list (a narrow page only)."""
        if not self._narrow or self._open or self._move is not None:
            return
        self._open = True
        self._place()
        self._dim.show()
        self._dim.raise_()
        self.holder.show()
        self.holder.raise_()
        self.holder.move(self._host.width(), 0)
        self._slide_to(self._target(), SLIDE_IN, QEasingCurve.Type.OutCubic)

    def close(self) -> None:
        """Slide the column out to the right, a little faster than in."""
        if not self._narrow or not self._open:
            return
        self._open = False
        self._dim.hide()
        self._slide_to(
            QPoint(self._host.width(), 0),
            SLIDE_OUT,
            QEasingCurve.Type.InCubic,
            on_done=self._hide_if_closed,
        )

    def _hide_if_closed(self) -> None:
        if not self._open:
            self.holder.hide()

    def _slide_to(self, end: QPoint, duration: int, curve, on_done=None) -> None:
        if self._slide is not None:
            self._slide.stop()
        self._slide = QPropertyAnimation(self.holder, b"pos", self)
        self._slide.setDuration(duration)
        self._slide.setEasingCurve(curve)
        self._slide.setStartValue(self.holder.pos())
        self._slide.setEndValue(end)
        if on_done is not None:
            self._slide.finished.connect(on_done)
        self._slide.start()

    def eventFilter(self, obj, e):  # noqa: N802 - Qt API
        if obj is self._host and e.type() == QEvent.Type.Resize:
            self._place()
        return False
