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
Window Controls - Title bar buttons and window management
"""

from PySide6.QtWidgets import QPushButton, QSizePolicy, QScrollArea
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath

from sok.ui.theme import Theme, svg_icon
from sok.ui.components.base import parse_color


class WindowControlButton(QPushButton):
    """Window control button for minimize/maximize/close.

    A styled button with hover effects and optional rounded corner.

    Attributes:
        top_right_radius: Radius for top-right corner rounding.
    """

    def __init__(self, icon_name: str, hover_color: str | None = None, parent=None):
        """Initialize the window control button.

        Args:
            icon_name: Name of the SVG icon.
            hover_color: Optional hover background color.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._icon_name = icon_name
        self._hover_color = hover_color
        self._hovered = False
        self.top_right_radius = 0

        self.setMinimumWidth(42)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def enterEvent(self, e):
        """Handle mouse enter.

        Args:
            e: Enter event.
        """
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        """Handle mouse leave.

        Args:
            e: Leave event.
        """
        self._hovered = False
        self.update()

    def paintEvent(self, e):
        """Paint the control button.

        Args:
            e: Paint event.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.window().c if hasattr(self.window(), "c") else Theme.DARK  # type: ignore[union-attr]

        if self._hovered:
            hc = self._hover_color or c.get("hover", "rgba(255, 255, 255, 0.15)")
            color = parse_color(hc)

            if self.top_right_radius > 0:
                r = self.top_right_radius
                w, h = self.width(), self.height()
                path = QPainterPath()
                path.moveTo(0, 0)
                path.lineTo(w - r, 0)
                path.arcTo(w - 2 * r, 0, 2 * r, 2 * r, 90, -90)
                path.lineTo(w, h)
                path.lineTo(0, h)
                path.closeSubpath()
                p.fillPath(path, color)
            else:
                p.fillRect(self.rect(), color)

        icon = svg_icon(self._icon_name, "#FFFFFF", 20)
        p.drawPixmap((self.width() - 20) // 2, (self.height() - 20) // 2, icon)


class StopPropagationScrollArea(QScrollArea):
    """QScrollArea that prevents scroll event propagation to parent.

    Accepts scroll events when scrollbar has content, preventing
    parent widgets from receiving the event.
    """

    def wheelEvent(self, event):
        """Handle mouse wheel event.

        Args:
            event: Wheel event.
        """
        if self.verticalScrollBar().maximum() > 0:
            super().wheelEvent(event)
            event.accept()
        else:
            super().wheelEvent(event)
