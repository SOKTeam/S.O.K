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
"""Building blocks of the settings screen, from its mockup.

A section is a title on the left (200px) and its content on the right,
under a hairline. Inside, the settings are plain lines: no card, no shadow.
A yes/no setting is a small square box, accent when on; a choice among a
few words is a row of small keys, the chosen one in the accent.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sok.ui.components.base import KeyButton, parse_color
from sok.ui.theme import Theme, ui_font

# Width of the title column of a section.
TITLE_WIDTH = 200


def _palette(widget: QWidget) -> dict[str, str]:
    return getattr(widget.window(), "c", None) or Theme.DARK


class Lines(QWidget):
    """The settings of a section, one under the other, 14px apart.

    It replaces the old cards: same add() as Card, without the separators.
    """

    def __init__(self, spacing: int = 14, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(spacing)

    def add(self, widget: QWidget, last: bool = False) -> None:  # noqa: ARG002
        self._layout.addWidget(widget)


class SettingsBlock(QWidget):
    """A section: its title on the left, its content on the right."""

    def __init__(self, body: QWidget, parent=None):
        super().__init__(parent)
        grid = QGridLayout(self)
        grid.setContentsMargins(14, 26, 14, 26)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(0)
        self.title = QLabel()
        title = ui_font(17, 600)
        title.setLetterSpacing(title.SpacingType.AbsoluteSpacing, -0.34)
        self.title.setFont(title)
        self.title.setFixedWidth(TITLE_WIDTH)
        self.title.setWordWrap(True)
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        grid.addWidget(self.title, 0, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(body, 0, 1)
        grid.setColumnStretch(1, 1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, e):  # noqa: N802 - Qt API
        # The hairline above the section (CSS: inset 0 1px 0 var(--hair)).
        p = QPainter(self)
        p.setPen(QPen(parse_color(_palette(self)["line"]), 1))
        p.drawLine(QPointF(0, 0.5), QPointF(self.width(), 0.5))
        p.end()

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            c = _palette(self)
            self.title.setStyleSheet(f"color: {c['ink']}; background: transparent;")


class CheckBox(QWidget):
    """An 18px square box: accent with a check when on, an outline when off.

    Same signals and methods as Toggle, so it takes its place.
    """

    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def isChecked(self) -> bool:  # noqa: N802 - Qt API
        return self._on

    def setChecked(self, on: bool) -> None:  # noqa: N802 - Qt API
        on = bool(on)
        if on != self._on:
            self._on = on
            self.update()
            if not self.signalsBlocked():
                self.toggled.emit(on)

    def toggle(self) -> None:
        self.setChecked(not self._on)

    def mouseReleaseEvent(self, e):  # noqa: N802 - Qt API
        if self.isEnabled() and self.rect().contains(e.position().toPoint()):
            self.toggle()

    def keyPressEvent(self, e):  # noqa: N802 - Qt API
        if e.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.toggle()
        else:
            super().keyPressEvent(e)

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.4)
        rect = QRectF(self.rect())
        if self._on:
            path = QPainterPath()
            path.addRoundedRect(rect, 6, 6)
            p.fillPath(path, parse_color(c["accent"]))
            # Light from above (CSS: inset 0 1px 0 rgba(255,255,255,0.3)).
            p.setPen(QPen(parse_color("rgba(255,255,255,0.3)"), 1))
            p.drawLine(QPointF(5, 0.5), QPointF(13, 0.5))
            pen = QPen(parse_color(c["on-accent"]), 2.0)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            check = QPainterPath(QPointF(5.2, 9.4))
            check.lineTo(QPointF(7.9, 12.1))
            check.lineTo(QPointF(13, 6.4))
            p.drawPath(check)
        else:
            p.setPen(QPen(parse_color(c["line-strong"]), 1.5))
            p.drawRoundedRect(rect.adjusted(0.75, 0.75, -0.75, -0.75), 6, 6)
        if self.hasFocus():
            p.setPen(QPen(parse_color(c["accent"]), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)
        p.end()


class CheckLine(QWidget):
    """A box and its sentence, the whole line clickable."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.box = CheckBox()
        self.label = QLabel()
        self.label.setObjectName("SettingText")
        self.label.setFont(ui_font(14))
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.box)
        layout.addWidget(self.label, 1)

    def mouseReleaseEvent(self, e):  # noqa: N802 - Qt API
        if self.box.isEnabled():
            self.box.toggle()


class Choice(QWidget):
    """A row of small keys, one of them chosen (in the accent).

    Signals:
        chosen(str): The value of the key clicked.
    """

    chosen = Signal(str)

    def __init__(self, values: Iterable[str], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self._keys: List[Tuple[str, KeyButton]] = []
        self._value: Optional[str] = None
        for value in values:
            key = KeyButton("", small=True)
            key.clicked.connect(lambda _=False, v=value: self._click(v))
            layout.addWidget(key)
            self._keys.append((value, key))
        layout.addStretch()

    def set_texts(self, texts: Iterable[str]) -> None:
        for (_value, key), text in zip(self._keys, texts):
            key.setText(text)

    def value(self) -> Optional[str]:
        return self._value

    def set_value(self, value: Optional[str]) -> None:
        self._value = value
        for v, key in self._keys:
            key.set_primary(v == value)
            key.setAccessibleDescription("pressed" if v == value else "")

    def _click(self, value: str) -> None:
        if value != self._value:
            self.set_value(value)
            self.chosen.emit(value)


class VariableChip(QLabel):
    """A variable of a name model, such as {title}: click to insert it.

    Signals:
        picked(str): The variable, with its braces.
    """

    picked = Signal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        # Kept apart: the window stylesheet replaces the family of setFont.
        self._font = ui_font(11, 400, mono=True)
        self.setFont(self._font)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hover = False

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        width = QFontMetrics(self._font).horizontalAdvance(self.text())
        return QSize(width + 12, 18)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return self.sizeHint()

    def enterEvent(self, e):  # noqa: N802 - Qt API
        self._hover = True
        self.update()

    def leaveEvent(self, e):  # noqa: N802 - Qt API
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, e):  # noqa: N802 - Qt API
        self.picked.emit(self.text())

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(parse_color(c["line-strong"]), 1))
        p.drawRoundedRect(rect, 5, 5)
        p.setFont(self._font)
        p.setPen(parse_color(c["ink"] if self._hover else c["ink-muted"]))
        p.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()


def settings_stylesheet(c: dict[str, str], root: str) -> str:
    """Rules for the widgets of the settings, under the widget #root.

    Fields: Geist Mono 14px, 40px high, radius 10, a faint face and a 1px
    ring (mockup 07). The tones of the statuses follow the art direction:
    no green, "ok" is plain ink.
    """
    mono = Theme.MONO
    return f"""
        #{root} {{ background: transparent; }}
        #{root} QLabel {{ background: transparent; color: {c["ink"]}; }}
        #{root} QLabel#RowTitle, #{root} QLabel#SettingText {{
            color: {c["ink"]}; font-size: 14px;
        }}
        #{root} QLabel#RowSubtitle, #{root} QLabel#SettingHint {{
            color: {c["ink-faint"]}; font-size: 13px;
        }}
        #{root} QLabel#SettingMuted, #{root} QLabel#CategoryLabel {{
            color: {c["ink-muted"]}; font-size: 14px;
        }}
        #{root} QLabel#CategoryLabel {{
            font-weight: 400; letter-spacing: 0; margin: 12px 0 0 0; padding: 0; qproperty-indent: 0;
        }}
        #{root} QLabel#SettingPath {{
            color: {c["ink"]}; font-family: '{mono}'; font-size: 13px;
        }}
        #{root} QLabel#SettingPath[empty="true"] {{ color: {c["ink-faint"]}; }}
        #{root} QLabel[tone="ok"], #{root} QLabel#RowSubtitle[tone="ok"],
        #{root} QLabel#SettingHint[tone="ok"] {{ color: {c["ink-muted"]}; }}
        #{root} QLabel[tone="warn"], #{root} QLabel#RowSubtitle[tone="warn"],
        #{root} QLabel#SettingHint[tone="warn"] {{ color: {c["caution"]}; }}
        #{root} QLabel[tone="error"], #{root} QLabel#RowSubtitle[tone="error"],
        #{root} QLabel#SettingHint[tone="error"] {{ color: {c["danger"]}; }}
        #{root} QLabel[tone="info"], #{root} QLabel#RowSubtitle[tone="info"],
        #{root} QLabel#SettingHint[tone="info"] {{ color: {c["ink-faint"]}; }}
        #{root} QLineEdit {{
            font-family: '{mono}'; font-size: 14px;
            min-height: 40px; max-height: 40px; padding: 0 12px;
            border-radius: 10px; border: 1px solid {c["line-strong"]};
            background: {c["highlight"]}; color: {c["ink"]};
            selection-background-color: {c["accent-soft"]};
            selection-color: {c["ink"]};
        }}
        #{root} QLineEdit:focus {{ border-color: {c["accent"]}; }}
        #{root} QLineEdit#SettingsInput, #{root} QLineEdit#SettingsFormatInput {{
            min-height: 32px; max-height: 32px; font-size: 13px; border-radius: 8px;
        }}
        #{root} QComboBox {{
            font-size: 13px; min-height: 32px; max-height: 32px; padding: 0 10px;
            border-radius: 8px; border: 1px solid {c["line-strong"]};
            background: {c["highlight"]}; color: {c["ink"]};
        }}
        #{root} QComboBox:hover {{ border-color: {c["ink-faint"]}; }}
        #{root} QComboBox QAbstractItemView {{
            background: {c["surface-raised"]}; color: {c["ink"]};
            border: 1px solid {c["line-strong"]}; border-radius: 10px; padding: 4px;
            selection-background-color: {c["key"]}; selection-color: {c["ink"]};
        }}
        #{root} QComboBox QAbstractItemView::item {{
            min-height: 28px; padding-left: 8px; border-radius: 6px; color: {c["ink"]};
        }}
        #{root} QComboBox QAbstractItemView::item:selected,
        #{root} QComboBox QAbstractItemView::item:hover {{
            background: {c["key"]}; color: {c["ink"]};
        }}
        #{root} QPushButton#PatternRemoveBtn {{
            background: transparent; border: none; border-radius: 6px;
            color: {c["ink-faint"]}; font-size: 15px;
        }}
        #{root} QPushButton#PatternRemoveBtn:hover {{
            background: {c["highlight"]}; color: {c["ink"]};
        }}
    """
