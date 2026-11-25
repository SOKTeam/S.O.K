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

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QFont, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import QBoxLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from sok.ui.components.base import KeyButton, parse_color
from sok.ui.motion import SLIDE_IN, SLIDE_OUT
from sok.ui.theme import ui_font

# Widest the navigation and the pages get; past it they are centered.
MAX_CONTENT_WIDTH = 1760

# The right column: about 36% of the page, from 320 to 520px (the mockups
# give it 420 to 520).
SIDE_SHARE = 0.36
SIDE_MIN, SIDE_MAX = 320, 520

# Narrowest page that shows its right column beside the list; below, the
# column opens over the list (SidePanel).
NARROW_WIDTH = 1000

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

    Args:
        host: The screen holding the list and the column.
        layout: The layout of the host the column is added to.
        side: The column (scene, pick panel, summary…).
        back_text: Gives the translated text of the key back to the list.
    """

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
        self._back_text = back_text
        self._back = KeyButton("", small=True)
        self._back.clicked.connect(self.close)
        self.holder = _Holder(side, self._back)
        layout.addWidget(self.holder)
        self._dim = _Dim(self.close, host)
        self._narrow = False
        self._open = False
        self._slide: Optional[QPropertyAnimation] = None
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
        if page_width < NARROW_WIDTH:
            return max(SIDE_MIN, min(560, round(page_width * 0.62)))
        return side_width(page_width)

    def fit(self, page_width: int) -> None:
        """Beside the list or over it, from the width of the page."""
        narrow = page_width < NARROW_WIDTH
        if narrow != self._narrow:
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
        self._place()

    def _target(self) -> QPoint:
        return QPoint(self._host.width() - self.holder.width(), 0)

    def _place(self) -> None:
        if not self._narrow:
            return
        width = self.column_width(self._host.width())
        self.holder.resize(width, self._host.height())
        self.holder.move(
            self._target() if self._open else QPoint(self._host.width(), 0)
        )
        self._dim.setGeometry(self._host.rect())

    def open(self) -> None:
        """Slide the column over the list (a narrow page only)."""
        if not self._narrow or self._open:
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
