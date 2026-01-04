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
"""Helpers for window chrome behaviors (hit test, drag)."""

from PySide6.QtCore import QRect


def hit_test_resize(x: int, y: int, frame: QRect, border_width: int = 6) -> int:
    """Return HT* code for resize zones, or 0x1 (HTCLIENT).

    Args:
        x: global mouse x
        y: global mouse y
        frame: window frame geometry
        border_width: detection margin in px
    """
    lx = x - frame.x()
    ly = y - frame.y()
    w = frame.width()
    h = frame.height()

    left = lx < border_width
    right = lx > w - border_width
    top = ly < border_width
    bottom = ly > h - border_width

    if top and left:
        return 0xD  # HTTOPLEFT
    if top and right:
        return 0xE  # HTTOPRIGHT
    if bottom and left:
        return 0x10  # HTBOTTOMLEFT
    if bottom and right:
        return 0x11  # HTBOTTOMRIGHT
    if left:
        return 0xA  # HTLEFT
    if right:
        return 0xB  # HTRIGHT
    if top:
        return 0xC  # HTTOP
    if bottom:
        return 0xF  # HTBOTTOM
    return 0x1  # HTCLIENT
