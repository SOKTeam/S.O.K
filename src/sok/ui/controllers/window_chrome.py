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

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QWidget


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


Edge = Qt.Edge
Cursor = Qt.CursorShape

# Edges each grip resizes, with the cursor shown over it.
_GRIPS = (
    (Edge.LeftEdge, Cursor.SizeHorCursor),
    (Edge.RightEdge, Cursor.SizeHorCursor),
    (Edge.TopEdge, Cursor.SizeVerCursor),
    (Edge.BottomEdge, Cursor.SizeVerCursor),
    (Edge.TopEdge | Edge.LeftEdge, Cursor.SizeFDiagCursor),
    (Edge.BottomEdge | Edge.RightEdge, Cursor.SizeFDiagCursor),
    (Edge.TopEdge | Edge.RightEdge, Cursor.SizeBDiagCursor),
    (Edge.BottomEdge | Edge.LeftEdge, Cursor.SizeBDiagCursor),
)


class _ResizeGrip(QWidget):
    """Invisible strip that starts a system resize when pressed."""

    def __init__(self, window: QWidget, edges: Qt.Edge, cursor: Qt.CursorShape):
        """Create the grip over the window.

        Args:
            window: Frameless top-level window.
            edges: Edges resized by dragging the grip.
            cursor: Cursor shown over the grip.
        """
        super().__init__(window)
        self.edges = edges
        self.setCursor(cursor)

    def mousePressEvent(self, event):
        """Hand the resize to the window manager (works on Wayland and X11).

        Args:
            event: Mouse event.
        """
        handle = self.window().windowHandle()
        if event.button() == Qt.MouseButton.LeftButton and handle:
            handle.startSystemResize(self.edges)


class ResizeGrips:
    """Resize borders of a frameless window, for Linux.

    Windows resizes the frameless window through WM_NCHITTEST; Linux has no
    equivalent, so invisible grips along the edges and corners ask the
    window manager to resize instead.
    """

    def __init__(self, window: QWidget, border_width: int = 6):
        """Create the grips.

        Args:
            window: Frameless top-level window.
            border_width: Thickness of the grips in px.
        """
        self._border = border_width
        self._grips = [_ResizeGrip(window, e, c) for e, c in _GRIPS]

    def update_geometry(self, width: int, height: int) -> None:
        """Lay the grips along the window edges and keep them on top.

        Args:
            width: Window width.
            height: Window height.
        """
        b = self._border
        for grip in self._grips:
            e = grip.edges
            left, right = bool(e & Edge.LeftEdge), bool(e & Edge.RightEdge)
            top, bottom = bool(e & Edge.TopEdge), bool(e & Edge.BottomEdge)
            # Side grips stop where the corner grips start.
            x = width - b if right else 0 if left else b
            y = height - b if bottom else 0 if top else b
            w = b if left or right else width - 2 * b
            h = b if top or bottom else height - 2 * b
            grip.setGeometry(x, y, w, h)
            grip.raise_()

    def set_visible(self, visible: bool) -> None:
        """Show the grips, or hide them while the window is maximized.

        Args:
            visible: Whether the window can be resized.
        """
        for grip in self._grips:
            grip.setVisible(visible)
