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
"""The scroll bar of S.O.K: thin, over the content, shown only when needed.

The bar of the system stays hidden and keeps doing the scrolling (wheel,
trackpad, keys); this one only shows where the content is. It is invisible
at rest, comes in when the content scrolls or when the mouse nears the right
edge, and fades out a second later. It is 4px wide, 8px under the mouse so
that it can be grabbed, in the color of the text, faint. The same on macOS,
Windows and Linux, whatever the mouse.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QObject, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QWidget

from sok.ui.components.base import parse_color
from sok.ui.motion import animate
from sok.ui.theme import Theme

# Width of the place it takes at the right edge, of the bar at rest and
# under the mouse, and its gap to the edge and to the ends.
RAIL = 14
THIN = 4
WIDE = 8
MARGIN = 3
# The mouse this close to the right edge brings the bar in.
EDGE = 24
# Shortest bar, so that it can always be grabbed.
MIN_LENGTH = 28
# How long it stays after the last scroll, and its fades (ms).
LINGER = 1000
FADE_IN = 120
FADE_OUT = 300
# Strength of the text color, at rest and under the mouse.
ALPHA = 0.28
ALPHA_HOVER = 0.42


class ThinScrollBar(QWidget):
    """The thin bar over the right edge of a scroll area (vertical only)."""

    def __init__(self, area: QAbstractScrollArea):
        super().__init__(area)
        self._area = area
        # Kept: events of the viewport still come while the area is freed.
        self._viewport = area.viewport()
        self._bar = area.verticalScrollBar()
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._opacity = 0.0
        self._hovered = False
        # While the bar is dragged: where it was grabbed, from its top.
        self._grab: Optional[float] = None
        self._fade: Optional[QVariantAnimation] = None
        self._linger = QTimer(self)
        self._linger.setSingleShot(True)
        self._linger.setInterval(LINGER)
        self._linger.timeout.connect(self._fade_out)
        self._bar.valueChanged.connect(self._on_scroll)
        self._bar.rangeChanged.connect(self._on_range)
        area.installEventFilter(self)
        self._viewport.installEventFilter(self)
        self._viewport.setMouseTracking(True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._place()

    # ------------------------------------------------------------- Place

    def _place(self) -> None:
        port = self._viewport.geometry()
        self.setGeometry(port.right() + 1 - RAIL, port.top(), RAIL, port.height())
        self.raise_()

    def _span(self) -> int:
        return self._bar.maximum() - self._bar.minimum()

    def handle_rect(self) -> Optional[QRectF]:
        """Where the bar is drawn, or None when nothing scrolls."""
        span = self._span()
        if span <= 0:
            return None
        room = self.height() - 2 * MARGIN
        page = max(1, self._bar.pageStep())
        length = min(room, max(MIN_LENGTH, room * page / (span + page)))
        top = (
            MARGIN + (room - length) * (self._bar.value() - self._bar.minimum()) / span
        )
        width = WIDE if self._hovered or self._grab is not None else THIN
        return QRectF(self.width() - MARGIN - width, top, width, length)

    # ------------------------------------------------------------ Showing

    def wake(self) -> None:
        """Show the bar, and let it fade out a moment after."""
        if self._span() <= 0:
            return
        if self._opacity < 1:
            self._fade_to(1.0, FADE_IN)
        self._linger.start()

    def _fade_out(self) -> None:
        if self._hovered or self._grab is not None:
            self._linger.start()
            return
        self._fade_to(0.0, FADE_OUT)

    def _fade_to(self, opacity: float, duration: int) -> None:
        if self._fade is not None:
            self._fade.stop()
        self._fade = animate(
            self, duration, self._set_opacity, self._opacity, opacity, self._faded
        )

    def _faded(self) -> None:
        self._fade = None

    def _set_opacity(self, opacity: float) -> None:
        self._opacity = opacity
        self.update()

    def _on_scroll(self, _value: int) -> None:
        self.update()
        self.wake()

    def _on_range(self, _low: int, _high: int) -> None:
        if self._span() <= 0:
            self._set_opacity(0.0)
        self.update()

    def eventFilter(self, obj: QObject, e: QEvent) -> bool:  # noqa: N802 - Qt API
        kind = e.type()
        if obj is self._area and kind in (
            QEvent.Type.Resize,
            QEvent.Type.LayoutRequest,
        ):
            self._place()
        elif obj is self._viewport:
            if kind == QEvent.Type.Resize:
                self._place()
            elif kind == QEvent.Type.MouseMove:
                x = e.position().x()  # type: ignore[attr-defined]
                if x > self._viewport.width() - EDGE:
                    self.wake()
        return False

    # -------------------------------------------------------------- Mouse

    def enterEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = True
        self.wake()
        self.update()

    def leaveEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = False
        self._linger.start()
        self.update()

    def mousePressEvent(self, e):  # noqa: N802 - Qt API
        rect = self.handle_rect()
        if rect is None or e.button() != Qt.MouseButton.LeftButton:
            return
        y = e.position().y()
        if rect.top() <= y <= rect.bottom():
            self._grab = y - rect.top()
        else:
            # A click beside the bar brings its middle there.
            self._grab = rect.height() / 2
            self._drag_to(y)
        self.update()

    def mouseMoveEvent(self, e):  # noqa: N802 - Qt API
        if self._grab is not None:
            self._drag_to(e.position().y())

    def mouseReleaseEvent(self, e):  # noqa: N802 - Qt API
        self._grab = None
        self._linger.start()
        self.update()

    def _drag_to(self, y: float) -> None:
        rect = self.handle_rect()
        if rect is None or self._grab is None:
            return
        room = self.height() - 2 * MARGIN - rect.height()
        share = (y - self._grab - MARGIN) / room if room > 0 else 0.0
        share = min(1.0, max(0.0, share))
        self._bar.setValue(self._bar.minimum() + round(share * self._span()))

    def wheelEvent(self, e):  # noqa: N802 - Qt API
        # The wheel over the bar scrolls the content as everywhere else.
        QApplication.sendEvent(self._viewport, e)

    # -------------------------------------------------------------- Paint

    def paintEvent(self, e):  # noqa: N802 - Qt API
        rect = self.handle_rect()
        if rect is None or self._opacity <= 0:
            return
        c = getattr(self.window(), "c", None) or Theme.DARK
        color = QColor(parse_color(c["ink"]))
        strong = self._hovered or self._grab is not None
        color.setAlphaF((ALPHA_HOVER if strong else ALPHA) * self._opacity)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        radius = rect.width() / 2
        p.drawRoundedRect(rect, radius, radius)
        p.end()


def thin_scroll_bar(area: QAbstractScrollArea) -> ThinScrollBar:
    """Give a scroll area the thin bar of S.O.K in place of the system's."""
    return ThinScrollBar(area)
