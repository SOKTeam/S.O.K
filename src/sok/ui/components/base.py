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
Base UI Components - Cards, Rows, Toggles and Buttons
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget, QPushButton
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property, QRect
from PySide6.QtGui import QPainter, QColor, QFont

from sok.ui.theme import Theme
import logging

logger = logging.getLogger(__name__)


def parse_color(value) -> QColor:
    """Parse color from string (handles rgba css style) or return QColor"""
    if isinstance(value, QColor):
        return value
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("rgba"):
            try:
                # rgba(255, 255, 255, 0.15)
                content = value[value.find("(") + 1 : value.find(")")]
                parts = content.split(",")
                if len(parts) == 4:
                    r = int(parts[0].strip())
                    g = int(parts[1].strip())
                    b = int(parts[2].strip())
                    a_str = parts[3].strip()
                    if "." in a_str:
                        a = int(float(a_str) * 255)
                    else:
                        a = int(a_str)
                    return QColor(r, g, b, a)
            except (ValueError, TypeError) as exc:
                logger.debug("Failed to parse rgba color %s", value, exc_info=exc)
        return QColor(value)
    return QColor()


class Card(QFrame):
    """Card container widget.

    A styled frame that can contain multiple widgets with separators.

    Attributes:
        _layout: Internal vertical layout.
    """

    def __init__(self, parent=None):
        """Initialize the card.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def add(self, widget, last=False):
        """Add a widget to the card.

        Args:
            widget: Widget to add.
            last: If True, no separator is added before.
        """
        if self._layout.count() > 0 and not last:
            sep = QFrame()
            sep.setFixedHeight(1)
            sep.setObjectName("Separator")
            self._layout.addWidget(sep)
        self._layout.addWidget(widget)


class Row(QWidget):
    """Simple data row for settings and info display.

    Renders a title with optional subtitle, value, and chevron indicator.

    Attributes:
        clicked: Signal emitted when row is clicked.
        _title: Row title text.
        _subtitle: Row subtitle text.
        _value: Value displayed on the right.
        _chevron: Whether to show the chevron indicator.
        _hovered: Current hover state.
    """

    clicked = Signal()

    def __init__(self, title: str, subtitle: str = "", icon: str = "", parent=None):
        """Initialize the row.

        Args:
            title: Row title text.
            subtitle: Optional subtitle text.
            icon: Optional icon name (unused).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        self._icon = icon
        self._value = ""
        self._chevron = True
        self._hovered = False

        self.setFixedHeight(44 if subtitle else 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def set_value(self, v: str):
        """Set the displayed value.

        Args:
            v: Value text to display.
        """
        self._value = v
        self.update()

    def set_title(self, title: str):
        """Set the row title.

        Args:
            title: New title text.
        """
        self._title = title
        self.update()

    def set_chevron(self, show: bool):
        """Set chevron visibility.

        Args:
            show: Whether to show the chevron.
        """
        self._chevron = show
        self.update()

    def mousePressEvent(self, event):
        """Handle mouse press event.

        Args:
            event: Mouse event.
        """
        self.clicked.emit()

    def enterEvent(self, e):
        """Handle mouse enter event.

        Args:
            e: Enter event.
        """
        self._hovered = True
        self.update()

    def leaveEvent(self, e):
        """Handle mouse leave event.

        Args:
            e: Leave event.
        """
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        """Paint the row.

        Args:
            event: Paint event.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.window().c if hasattr(self.window(), "c") else Theme.DARK  # type: ignore[union-attr]

        if self._hovered:
            bg = parse_color(c.get("hover", "rgba(255,255,255,0.1)"))
            p.fillRect(self.rect(), bg)

        x = 12

        p.setPen(parse_color(c["text"]))
        p.setFont(QFont(Theme.FONT, 13))

        if self._subtitle:
            p.drawText(QRect(x, 6, 300, 18), Qt.AlignmentFlag.AlignVCenter, self._title)
            p.setPen(parse_color(c["secondary"]))
            p.setFont(QFont(Theme.FONT, 11))
            p.drawText(
                QRect(x, 24, 300, 16), Qt.AlignmentFlag.AlignVCenter, self._subtitle
            )
        else:
            p.drawText(
                QRect(x, 0, 300, self.height()),
                Qt.AlignmentFlag.AlignVCenter,
                self._title,
            )

        right = self.width() - 12
        if self._value:
            p.setPen(parse_color(c["secondary"]))
            p.setFont(QFont(Theme.FONT, 13))
            p.drawText(
                QRect(right - 150, 0, 140, self.height()),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                self._value,
            )

        if self._chevron:
            p.setPen(parse_color(c["tertiary"]))
            p.setFont(QFont(Theme.FONT, 14, QFont.Weight.Bold))
            p.drawText(
                QRect(right - 8, 0, 16, self.height()),
                Qt.AlignmentFlag.AlignCenter,
                "›",
            )


class Toggle(QWidget):
    """Toggle switch widget.

    Animated on/off switch with custom painting.

    Attributes:
        toggled: Signal emitted with new state when toggled.
        _on: Current toggle state.
        _x: Knob x position for animation.
    """

    toggled = Signal(bool)

    def __init__(self, parent=None):
        """Initialize the toggle.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setFixedSize(38, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._on = True
        self._x = 18.0
        self._anim = QPropertyAnimation(self, b"knob")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def isChecked(self):
        """Get the current toggle state.

        Returns:
            True if toggle is on, False otherwise.
        """
        return self._on

    def setChecked(self, v):
        """Set the toggle state.

        Args:
            v: New state (True for on, False for off).
        """
        self._on = v
        self._x = 18.0 if v else 2.0
        self.update()

    def get_knob(self):
        """Get the knob position.

        Returns:
            Current knob x position.
        """
        return self._x

    def set_knob(self, v):
        """Set the knob position.

        Args:
            v: New knob x position.
        """
        self._x = v
        self.update()

    knob = Property(float, get_knob, set_knob)

    def mousePressEvent(self, e):
        """Handle mouse press to toggle state.

        Args:
            e: Mouse event.
        """
        self._on = not self._on
        self._anim.stop()
        self._anim.setStartValue(self._x)
        self._anim.setEndValue(18.0 if self._on else 2.0)
        self._anim.start()
        self.toggled.emit(self._on)

    def paintEvent(self, e):
        """Paint the toggle switch.

        Args:
            e: Paint event.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.window().c if hasattr(self.window(), "c") else Theme.DARK  # type: ignore[union-attr]
        p.setBrush(parse_color(c["green"] if self._on else c["tertiary"]))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, 38, 22, 11, 11)
        p.setBrush(parse_color("#FFFFFF"))
        p.drawEllipse(int(self._x), 2, 18, 18)


class ActionButton(QPushButton):
    """Primary action button.

    Styled push button for primary actions.

    Attributes:
        Inherits all QPushButton attributes.
    """

    def __init__(self, text: str = "", parent=None):
        """Initialize the action button.

        Args:
            text: Button label text.
            parent: Parent widget.
        """
        super().__init__(text, parent)
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("ActionBtn")
        self.setStyleSheet("padding: 0 15px;")
