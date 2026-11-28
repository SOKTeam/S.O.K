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

from PySide6.QtWidgets import (
    QFrame,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QPropertyAnimation,
    QEasingCurve,
    Property,
    QPointF,
    QRect,
    QRectF,
    QSize,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
)

from sok.ui.platform import IS_MACOS
from sok.ui.theme import Theme, ui_font
from sok.ui.motion import PRESS, animate
from sok.ui.tokens import RADIUS, SPACE
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

    Animated on/off switch with custom painting. macOS keeps the Apple
    look (green track, large white knob); Windows and Linux get an
    outlined track when off and an accent track when on, with a small
    knob that grows under the mouse.

    Attributes:
        toggled: Signal emitted with new state when toggled.
        _on: Current toggle state.
        _x: Knob position for animation, from OFF_X to ON_X.
        _hovered: Whether the mouse is over the switch.
    """

    toggled = Signal(bool)

    OFF_X = 2.0
    ON_X = 18.0

    def __init__(self, parent=None):
        """Initialize the toggle.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        if IS_MACOS:
            self.setFixedSize(38, 22)
        else:
            self.setFixedSize(40, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._on = True
        self._x = self.ON_X
        self._hovered = False
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
        self._x = self.ON_X if v else self.OFF_X
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
        self._anim.setEndValue(self.ON_X if self._on else self.OFF_X)
        self._anim.start()
        self.toggled.emit(self._on)

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

    def paintEvent(self, e):
        """Paint the toggle switch.

        Args:
            e: Paint event.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.window().c if hasattr(self.window(), "c") else Theme.DARK  # type: ignore[union-attr]
        if IS_MACOS:
            p.setBrush(parse_color(c["accent"] if self._on else c["tertiary"]))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(0, 0, 38, 22, 11, 11)
            p.setBrush(parse_color("#FFFFFF"))
            p.drawEllipse(int(self._x), 2, 18, 18)
            return

        w, h = self.width(), self.height()
        radius = h / 2
        if self._on:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(parse_color(c["accent"]))
            p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)
            knob_color = c["accent_text"]
        else:
            p.setPen(QPen(parse_color(c["secondary"]), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(
                QRectF(0.5, 0.5, w - 1, h - 1), radius - 0.5, radius - 0.5
            )
            knob_color = c["secondary"]

        # The knob center slides from the left end to the right end.
        progress = (self._x - self.OFF_X) / (self.ON_X - self.OFF_X)
        cx = radius + progress * (w - 2 * radius)
        knob_r = 7.0 if self._hovered else 6.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(parse_color(knob_color))
        p.drawEllipse(QPointF(cx, radius), knob_r, knob_r)


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    """The color t of the way from a to b."""
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


class KeyButton(QPushButton):
    """The button of the art direction: a flat face lit from above.

    A 1px light line inside the top edge, a 1px shadow line under the bottom
    edge, no glow and no gradient. Pressed, the face gets darker and shrinks
    a little (scale 0.985) without moving.

    The primary button (coral face, near-black text) is used once per screen;
    every other action is a secondary one (graphite face). After the label
    come an optional count, in Geist Mono, and an optional shortcut engraved
    after a thin vertical line.

    Attributes:
        HEIGHT: Height of the face (regular, small); the shadow line adds 1px.
    """

    HEIGHT = (44, 32)
    PRESSED_SCALE = 0.985

    def __init__(
        self,
        text: str = "",
        parent=None,
        primary: bool = False,
        small: bool = False,
    ):
        """Initialize the button.

        Args:
            text: Label.
            parent: Parent widget.
            primary: Coral face, for the one main action of a screen.
            small: 32px high, for actions inside a row or a panel.
        """
        super().__init__(text, parent)
        self._primary = primary
        self._small = small
        self._danger = False
        self._count: int | None = None
        self._shortcut = ""
        self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(self.HEIGHT[small] + 1)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        # The accent ring is drawn only for the keyboard (CSS :focus-visible);
        # never the blue ring of macOS.
        self.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self._keyboard_focus = False
        # 0 at rest, 1 pressed: the face darkens and settles in 90ms.
        self._press = 0.0
        self.pressed.connect(lambda: self._animate_press(1.0))
        self.released.connect(lambda: self._animate_press(0.0))

    def _animate_press(self, target: float) -> None:
        animate(self, PRESS, self._set_press, start=self._press, end=target)

    def _set_press(self, value: float) -> None:
        self._press = value
        self.update()

    def focusInEvent(self, e):  # noqa: N802 - Qt API
        self._keyboard_focus = e.reason() in (
            Qt.FocusReason.TabFocusReason,
            Qt.FocusReason.BacktabFocusReason,
        )
        super().focusInEvent(e)

    def focusOutEvent(self, e):  # noqa: N802 - Qt API
        self._keyboard_focus = False
        super().focusOutEvent(e)

    def set_primary(self, primary: bool) -> None:
        """Use the coral face (True) or the graphite one (False)."""
        self._primary = primary
        self.update()

    def set_danger(self, danger: bool) -> None:
        """Write the label in the danger color, for a destructive action."""
        self._danger = danger
        self.update()

    def set_count(self, count: int | None) -> None:
        """Show the number of items the action applies to, or hide it."""
        self._count = count
        self.updateGeometry()
        self.update()

    def set_shortcut(self, shortcut: str) -> None:
        """Engrave a keyboard shortcut at the right ("⌘R"), or remove it."""
        self._shortcut = shortcut
        self.updateGeometry()
        self.update()

    def setText(self, text: str) -> None:  # noqa: N802 - Qt API
        """Set the label and resize the button to fit it."""
        super().setText(text)
        self.updateGeometry()

    def _fonts(self) -> tuple[QFont, QFont, QFont]:
        """Return the fonts of the label, the count and the shortcut."""
        size = 13 if self._small else 15
        label = ui_font(size, 600)
        label.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 99)
        return label, ui_font(size, 500, mono=True), ui_font(11, 500, mono=True)

    def _parts(self) -> list[tuple[str, QFont, int]]:
        """Return the texts drawn left to right, with their font and gap."""
        label, count, legend = self._fonts()
        gap = SPACE["2"] if self._small else SPACE["3"]
        parts = [(self.text(), label, 0)]
        if self._count is not None:
            parts.append((str(self._count), count, gap))
        if self._shortcut:
            # The vertical line, then the shortcut after a 12px padding.
            parts.append((self._shortcut, legend, gap + SPACE["3"]))
        return parts

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        """Width of the texts plus the side paddings."""
        padding = self._padding()
        width = sum(
            QFontMetrics(font).horizontalAdvance(text) + gap
            for text, font, gap in self._parts()
        )
        return QSize(width + 2 * padding, self.HEIGHT[self._small] + 1)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return self.sizeHint()

    def enterEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):  # noqa: N802 - Qt API
        """Paint the face, its two light lines, then the texts."""
        c = getattr(self.window(), "c", None) or Theme.DARK
        role = "accent" if self._primary else "key"
        shadow = "shadow-key-primary" if self._primary else "shadow-key"
        rest = c[f"{role}-hover"] if self._hovered and self.isEnabled() else c[role]
        # Between its color at rest and pressed, as the press goes.
        face_color = _mix(
            parse_color(rest), parse_color(c[f"{role}-pressed"]), self._press
        )
        if self._primary:
            ink = c["on-accent"]
        else:
            ink = c["danger"] if self._danger else c["ink"]

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.4)
        height = self.HEIGHT[self._small]
        face_rect = QRectF(0, 0, self.width(), height)
        if self._press > 0:
            scale = 1 - (1 - self.PRESSED_SCALE) * self._press
            center = face_rect.center()
            p.translate(center)
            p.scale(scale, scale)
            p.translate(-center)
        radius = RADIUS["key-sm"] if self._small else RADIUS["key"]

        p.setPen(Qt.PenStyle.NoPen)
        # Shadow line: the same shape 1px lower, under the face.
        p.setBrush(parse_color(c[f"{shadow}-drop"]))
        p.drawRoundedRect(face_rect.translated(0, 1), radius, radius)
        p.setBrush(face_color)
        p.drawRoundedRect(face_rect, radius, radius)
        # Light line inside the top edge: the face minus itself 1px lower.
        light = QPainterPath()
        light.addRoundedRect(face_rect, radius, radius)
        below = QPainterPath()
        below.addRoundedRect(face_rect.translated(0, 1), radius, radius)
        p.setBrush(parse_color(c[f"{shadow}-light"]))
        p.drawPath(light.subtracted(below))

        if (
            self.hasFocus()
            and self._keyboard_focus
            and self.focusPolicy() != Qt.FocusPolicy.NoFocus
        ):
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(parse_color(c["accent"]), 2))
            p.drawRoundedRect(face_rect.adjusted(-3, -3, 3, 3), radius + 3, radius + 3)

        ink_color = parse_color(ink)
        x = float(self._padding())
        for i, (text, font, gap) in enumerate(self._parts()):
            x += gap
            is_shortcut = self._shortcut and i == len(self._parts()) - 1
            if is_shortcut:
                line = QColor(ink_color)
                line.setAlphaF(0.6)
                p.setPen(QPen(line, 1))
                line_x = x - SPACE["3"] + 0.5
                p.drawLine(QPointF(line_x, 12), QPointF(line_x, height - 12))
            color = QColor(ink_color)
            if is_shortcut:
                color.setAlphaF(0.6)
            p.setPen(color)
            p.setFont(font)
            width = QFontMetrics(font).horizontalAdvance(text)
            p.drawText(
                QRectF(x, 0, width + 1, height),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                text,
            )
            x += width
        p.end()

    def _padding(self) -> int:
        """Side padding of the texts."""
        return SPACE["3"] if self._small else 18


class ActionButton(KeyButton):
    """A button for an action: secondary (graphite) unless primary=True.

    Kept for the existing screens; it is a KeyButton.
    """
