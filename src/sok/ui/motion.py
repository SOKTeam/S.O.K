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
Every duration is at most 250ms, so nothing makes the user wait.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QEasingCurve, QObject, QPoint, Qt, QVariantAnimation
from PySide6.QtGui import QPixmap, QRegion
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

# Durations, in milliseconds.
PRESS = 90
CROSSFADE = 150
SORTED = 200
SLIDE_OUT = 180
SLIDE_IN = 220
SUMMARY = 240
GAUGE = 250


def animate(
    owner: QObject,
    duration: int,
    on_value: Callable[[float], None],
    start: float = 0.0,
    end: float = 1.0,
    on_done: Optional[Callable[[], None]] = None,
    curve: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QVariantAnimation:
    """Run on_value(t) from start to end over duration, kept alive by
    owner, which also stops it if it goes away."""
    animation = QVariantAnimation(owner)
    animation.setDuration(duration)
    animation.setStartValue(float(start))
    animation.setEndValue(float(end))
    animation.setEasingCurve(curve)
    # on_value is connected as it is: a lambda around it here crashes Qt
    # when owner is freed just after the animation ends (seen offscreen).
    animation.valueChanged.connect(on_value)
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
