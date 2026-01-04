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
Sidebar Components - Navigation buttons and menus
"""

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt, Property
from PySide6.QtGui import QPainter, QColor, QFont

from sok.ui.theme import Theme, svg_icon
from sok.ui.components.base import parse_color


class SidebarButton(QPushButton):
    """Sidebar navigation button with collapse support.

    A checkable button that animates between compact and expanded states.

    Attributes:
        sidebarProgress: Qt property for animation progress (0.0 to 1.0).
    """

    def __init__(self, text: str, icon_name: str, parent=None):
        """Initialize the sidebar button.

        Args:
            text: Button text label.
            icon_name: Name of the SVG icon.
            parent: Parent widget.
        """
        super().__init__(text, parent)
        self._icon = icon_name
        self._hovered = False
        self._progress = 1.0
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def set_progress(self, progress: float):
        """Set the sidebar expansion progress.

        Args:
            progress: Progress value from 0.0 (compact) to 1.0 (expanded).
        """
        self._progress = max(0.0, min(1.0, progress))
        self.update()

    def progress(self) -> float:
        """Get the current progress.

        Returns:
            Current progress value.
        """
        return self._progress

    sidebarProgress = Property(float, progress, set_progress)

    def enterEvent(self, event):
        """Handle mouse enter.

        Args:
            event: Enter event.
        """
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave.

        Args:
            event: Leave event.
        """
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        """Paint the sidebar button.

        Args:
            event: Paint event.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.window().c if hasattr(self.window(), "c") else Theme.DARK  # type: ignore[union-attr]
        prog = self._progress

        left_margin = 8 + (4 * prog)
        right_margin = 8 + (4 * prog)
        rect = self.rect().adjusted(int(left_margin), 4, -int(right_margin), -4)

        accent = c.get("accent", "#FFFFFF")
        accent_text = c.get("accent_text", "#000000")
        text_col = c.get("text", "#FFFFFF")
        icon_secondary = c.get("icon_secondary", text_col)
        is_light_accent = accent in ("#FFFFFF", "white", "#FFF")

        if is_light_accent:
            hover_color = QColor(255, 255, 255, 60)
        else:
            hover_color = parse_color(c.get("hover", "rgba(255, 255, 255, 0.15)"))

        is_compact = prog < 0.5
        if self.isChecked():
            p.setPen(Qt.PenStyle.NoPen)
            if is_compact:
                indicator_alpha = int(255 * (1.0 - prog * 2))
                accent_color = parse_color(accent)
                accent_color.setAlpha(indicator_alpha)
                p.setBrush(accent_color)
                p.drawRoundedRect(2, 10, 3, self.height() - 20, 1.5, 1.5)
                p.setBrush(hover_color)
                p.drawRoundedRect(rect, 6, 6)
            else:
                p.setBrush(parse_color(accent))
                p.drawRoundedRect(rect, 6, 6)
        elif self._hovered:
            p.setBrush(hover_color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect, 6, 6)

        if self.isChecked() and prog > 0.5:
            icon_color = accent_text if is_light_accent else "#FFFFFF"
        else:
            icon_color = icon_secondary

        icon = svg_icon(self._icon, icon_color, 18)
        compact_x = 27
        extended_x = 20
        icon_x = int(compact_x + (extended_x - compact_x) * prog)
        icon_y = (self.height() - icon.height()) // 2
        p.drawPixmap(icon_x, icon_y, icon)

        if prog > 0.3:
            text_alpha = int(255 * ((prog - 0.3) / 0.7))
            if self.isChecked():
                text_color = (
                    parse_color(accent_text) if is_light_accent else QColor("#FFFFFF")
                )
            else:
                text_color = parse_color(text_col)
            text_color.setAlpha(text_alpha)
            p.setPen(text_color)
            font_name = c.get("font", Theme.FONT)
            p.setFont(QFont(font_name, 12))
            p.drawText(
                rect.adjusted(32, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, self.text()
            )


class MenuButton(QPushButton):
    """Hamburger menu button.

    A button that displays three horizontal lines (hamburger icon).
    """

    def __init__(self, parent=None):
        """Initialize the menu button.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._hovered = False
        self.setFixedSize(72, 42)
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
        """Paint the menu button.

        Args:
            e: Paint event.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.window().c if hasattr(self.window(), "c") else Theme.DARK  # type: ignore[union-attr]

        if self._hovered:
            bg_col = c.get("dropdown_bg", c["card"])
            p.fillRect(self.rect(), parse_color(bg_col))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(parse_color(c["text"]))
        cx, cy = self.width() // 2, self.height() // 2
        w, h = 18, 2
        for offset in [-6, 0, 6]:
            p.drawRoundedRect(cx - w // 2, cy + offset - h // 2, w, h, 1, 1)
