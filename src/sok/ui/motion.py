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

from PySide6.QtCore import QEasingCurve, QObject, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

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
    owner, and replace the animation of the same owner and callback."""
    animation = QVariantAnimation(owner)
    animation.setDuration(duration)
    animation.setStartValue(float(start))
    animation.setEndValue(float(end))
    animation.setEasingCurve(curve)
    animation.valueChanged.connect(lambda value: on_value(float(value)))
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
