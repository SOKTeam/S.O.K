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
"""The few animations of the interface, kept short and rare.

Only the moments that change the state of things move: a panel that comes
in or leaves, an item recognized or sorted, the end of a rename, the switch
to the pick panel, the press of a key. What the user does over and over
(moving in a list, changing page, typing, scrolling, hovering) never moves.
Every duration is at most 250ms, so nothing makes the user wait, except the
poster that travels to its new place (fly(), about 400ms): the lines around
it come in at once, one after the other (rise()).
"""

from __future__ import annotations

from typing import Callable, Iterable, Optional, Union

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QPainter, QPixmap, QRegion
from PySide6.QtWidgets import QGraphicsEffect, QGraphicsOpacityEffect, QLabel, QWidget

# Durations, in milliseconds.
PRESS = 90
CROSSFADE = 150
SORTED = 200
SLIDE_OUT = 180
SLIDE_IN = 220
SUMMARY = 240
GAUGE = 250
# A poster travelling to its new place, and the lines that come in around it.
MOVE = 400
RISE = 220
STAGGER = 35
RISE_PX = 6


def move_curve() -> QEasingCurve:
    """Fast start, long soft landing: what moves seems to have weight."""
    curve = QEasingCurve(QEasingCurve.Type.BezierSpline)
    curve.addCubicBezierSegment(QPointF(0.32, 0.72), QPointF(0, 1), QPointF(1, 1))
    return curve


def animate(
    owner: QObject,
    duration: int,
    on_value: Callable[[float], None],
    start: float = 0.0,
    end: float = 1.0,
    on_done: Optional[Callable[[], None]] = None,
    curve: Union[QEasingCurve.Type, QEasingCurve] = QEasingCurve.Type.OutCubic,
    delay: int = 0,
) -> QVariantAnimation:
    """Run on_value(t) from start to end over duration, after delay (it
    stays at start meanwhile), kept alive by owner, which also stops it if
    it goes away."""
    animation = QVariantAnimation(owner)
    animation.setStartValue(float(start))
    animation.setEndValue(float(end))
    if delay <= 0:
        animation.setDuration(duration)
        animation.setEasingCurve(curve)
        # on_value is connected as it is: a lambda around it here crashes Qt
        # when owner is freed just after the animation ends (seen offscreen).
        animation.valueChanged.connect(on_value)
    else:
        easing = QEasingCurve(curve)
        total = delay + duration

        def step(value: float) -> None:
            elapsed = (
                (float(value) - start) / (end - start) * total
                if end != start
                else total
            )
            progress = min(1.0, max(0.0, (elapsed - delay) / duration))
            on_value(start + (end - start) * easing.valueForProgress(progress))

        animation.setDuration(total)
        animation.valueChanged.connect(step)
    if on_done is not None:
        animation.finished.connect(on_done)
    animation.start(QVariantAnimation.DeletionPolicy.DeleteWhenStopped)
    return animation


def fade_in(widget: QWidget, duration: int = CROSSFADE) -> None:
    """Show a widget that fades in, then turn the effect off (a disabled
    effect draws the widget directly, at no cost)."""
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)

    def done() -> None:
        effect.setEnabled(False)

    animate(widget, duration, effect.setOpacity, on_done=done)


def crossfade(
    host: QWidget,
    change: Callable[[], None],
    duration: int = CROSSFADE,
    on_value: Optional[Callable[[float], None]] = None,
) -> None:
    """Swap what host shows with change(), the old view fading out while
    the new one fades in, so the place is never empty.

    The old view is a picture of host laid over it, which lets the clicks
    through and goes away at the end. on_value(t) follows the fade, from 0
    (old view) to 1 (new view), for what host does not draw itself, like
    the light the window paints behind it.
    """
    if not host.isVisible() or host.width() <= 0 or host.height() <= 0:
        change()
        return
    # Drawn without the background, which is the window's light: a grab()
    # would fill it with a flat grey.
    ratio = host.devicePixelRatioF()
    picture = QPixmap(round(host.width() * ratio), round(host.height() * ratio))
    picture.setDevicePixelRatio(ratio)
    picture.fill(Qt.GlobalColor.transparent)
    host.render(picture, QPoint(0, 0), QRegion(), QWidget.RenderFlag.DrawChildren)
    change()
    old = QLabel(host)
    old.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    old.setStyleSheet("background: transparent;")
    old.setPixmap(picture)
    old.setGeometry(host.rect())
    effect = QGraphicsOpacityEffect(old)
    old.setGraphicsEffect(effect)
    old.show()
    old.raise_()

    def step(t: float) -> None:
        effect.setOpacity(1.0 - t)
        if on_value is not None:
            on_value(t)

    animate(old, duration, step, on_done=old.deleteLater)


class _Flight(QWidget):
    """A picture moving over host, from one rectangle to another."""

    def __init__(
        self, host: QWidget, pixmap: QPixmap, start: QRectF, end: QRectF, fade: bool
    ):
        super().__init__(host)
        self._fade = fade
        self._t = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._pixmap = pixmap
        self._start, self._end = QRectF(start), QRectF(end)
        self._rect = QRectF(start)
        self.setGeometry(host.rect())
        self.show()
        self.raise_()

    def set_progress(self, t: float) -> None:
        self._t = t
        a, b = self._start, self._end
        self._rect = QRectF(
            a.x() + (b.x() - a.x()) * t,
            a.y() + (b.y() - a.y()) * t,
            a.width() + (b.width() - a.width()) * t,
            a.height() + (b.height() - a.height()) * t,
        )
        self.update()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._fade:
            p.setOpacity(1.0 - self._t)
        p.drawPixmap(self._rect, self._pixmap, QRectF(self._pixmap.rect()))
        p.end()


def fly(
    host: QWidget,
    pixmap: QPixmap,
    start: QRectF,
    end: QRectF,
    duration: int = MOVE,
    delay: int = 0,
    on_done: Optional[Callable[[], None]] = None,
    fade: bool = False,
) -> None:
    """Move a picture over host from start to end (rectangles in host),
    then take it away and call on_done: the place it lands on shows the
    real thing again. With fade, it fades out on the way (it has no place
    to land on)."""
    flight = _Flight(host, pixmap, start, end, fade)

    def done() -> None:
        flight.deleteLater()
        if on_done is not None:
            on_done()

    animate(
        flight,
        duration,
        flight.set_progress,
        on_done=done,
        curve=move_curve(),
        delay=delay,
    )


class _Rise(QGraphicsEffect):
    """Draws its widget faded and a little lower, until t reaches 1."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self._t = 0.0

    def set_progress(self, t: float) -> None:
        self._t = t
        self.update()

    def boundingRectFor(self, rect: Union[QRectF, QRect]) -> QRectF:  # noqa: N802 - Qt API
        return QRectF(rect).adjusted(0, 0, 0, RISE_PX)

    def draw(self, painter: QPainter) -> None:
        if self._t >= 1.0:
            self.drawSource(painter)
            return
        system = Qt.CoordinateSystem.LogicalCoordinates
        # PySide gives the picture without its offset: it is the top left
        # of the source rectangle.
        pixmap = self.sourcePixmap(system)
        top = self.sourceBoundingRect(system).topLeft()
        painter.save()
        painter.setOpacity(painter.opacity() * self._t)
        painter.drawPixmap(top + QPointF(0, RISE_PX * (1.0 - self._t)), pixmap)
        painter.restore()


def _hidden(widget: QWidget) -> bool:
    """Hidden on purpose. A widget just put in a layout is hidden too until
    Qt shows it, a moment later: that one comes in."""
    explicit = widget.testAttribute(Qt.WidgetAttribute.WA_WState_ExplicitShowHide)
    return widget.isHidden() and explicit


def rise(widget: QWidget, delay: int = 0, duration: int = RISE) -> None:
    """Bring a widget in: it fades in while rising 6px, after delay."""
    if _hidden(widget):
        return
    effect = _Rise(widget)
    widget.setGraphicsEffect(effect)

    def done() -> None:
        # Turned off rather than removed: removing it here would free the
        # animation that calls done(). Off, it draws the widget directly.
        effect.setEnabled(False)

    animate(effect, duration, effect.set_progress, on_done=done, delay=delay)


def cascade(
    widgets: Iterable[Optional[QWidget]], delay: int = 0, step: int = STAGGER
) -> int:
    """rise() the visible widgets one after the other; returns the delay
    after the last one, for what comes next."""
    for widget in widgets:
        if widget is None or _hidden(widget):
            continue
        rise(widget, delay)
        delay += step
    return delay
