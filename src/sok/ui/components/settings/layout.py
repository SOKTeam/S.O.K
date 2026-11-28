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
A yes/no setting is a small switch drawn like the keys; a choice among a
few words is the words themselves, the chosen one in ink. Lists of
values (name models, services) are dotted sheets whose lines open on a
click to show their field or keys.
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

from sok.ui.components.base import parse_color
from sok.ui.theme import Theme, ui_font

# Width of the title column of a section.
TITLE_WIDTH = 200
# The column of the titles narrows with the room, down to this.
TITLE_MIN_WIDTH = 140


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
        self._grid = grid
        self._body = body
        grid.addWidget(self.title, 0, 0, Qt.AlignmentFlag.AlignTop)
        grid.addWidget(body, 0, 1)
        grid.setColumnStretch(1, 1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_title_width(self, width: int) -> None:
        """Width of the column of the title, at the left of the content."""
        if self.title.width() != width:
            self.title.setFixedWidth(width)

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


class Switch(QWidget):
    """A small switch in the style of the keys: a flat face with a 1px
    highlight on top and a 1px shadow under it, no animation, no green.

    Off: the face of a key, a muted knob on the left. On: the accent face,
    a near-black knob on the right (on-accent, as text on the accent).
    Same signals and methods as Toggle, so it takes its place.
    """

    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False
        self._hover = False
        self.setFixedSize(32, 20)
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

    def set_hover(self, hover: bool) -> None:
        self._hover = hover
        self.update()

    def enterEvent(self, e):  # noqa: N802 - Qt API
        self.set_hover(True)

    def leaveEvent(self, e):  # noqa: N802 - Qt API
        self.set_hover(False)

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
        # The face leaves 1px under it for the shadow.
        face = QRectF(0, 0, self.width(), self.height() - 1)
        radius = face.height() / 2
        if self._on:
            color = c["accent-hover"] if self._hover else c["accent"]
            light, knob = c["shadow-key-primary-light"], c["on-accent"]
        else:
            color = c["key-hover"] if self._hover else c["key"]
            light, knob = c["shadow-key-light"], c["ink-muted"]
        shadow = QPainterPath()
        shadow.addRoundedRect(face.translated(0, 1), radius, radius)
        p.fillPath(shadow, parse_color(c["shadow-key-drop"]))
        path = QPainterPath()
        path.addRoundedRect(face, radius, radius)
        p.fillPath(path, parse_color(color))
        p.setPen(QPen(parse_color(light), 1))
        p.drawLine(QPointF(radius, 0.5), QPointF(face.width() - radius, 0.5))
        size = face.height() - 6
        x = face.width() - size - 3 if self._on else 3.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(parse_color(knob))
        p.drawEllipse(QRectF(x, 3, size, size))
        if self.hasFocus():
            p.setPen(QPen(parse_color(c["accent"]), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(
                face.adjusted(-2.5, -2.5, 2.5, 2.5), radius + 2, radius + 2
            )
        p.end()


class SwitchLine(QWidget):
    """A sentence and its switch at the right, the whole line clickable."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self.label = QLabel()
        self.label.setObjectName("SettingText")
        self.label.setFont(ui_font(14))
        self.box = Switch()
        layout.addWidget(self.label, 1)
        layout.addWidget(self.box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, e):  # noqa: N802 - Qt API
        self.box.set_hover(True)

    def leaveEvent(self, e):  # noqa: N802 - Qt API
        self.box.set_hover(False)

    def mouseReleaseEvent(self, e):  # noqa: N802 - Qt API
        if self.box.isEnabled():
            self.box.toggle()


class _Leader(QWidget):
    """The dotted line between a name and its value, 4px above the baseline."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(22)
        self.setMinimumWidth(16)
        self.baseline = 15

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        pen = QPen(parse_color(c["line-strong"]), 1, Qt.PenStyle.CustomDashLine)
        pen.setDashPattern([1, 2])
        p.setPen(pen)
        y = self.baseline - 4 + 0.5
        p.drawLine(QPointF(8, y), QPointF(self.width() - 8, y))
        p.end()


class SheetRow(QWidget):
    """A line of a dotted sheet (name ....... value) that opens on a click.

    The details (a field, keys…) are shown under it while it is open. The
    name and the value turn to ink under the mouse and while open.

    Signals:
        clicked: The line was clicked.
    """

    clicked = Signal()

    def __init__(self, mono_value: bool = False, parent=None):
        super().__init__(parent)
        self._open = False
        self._hover = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)
        self._line = QWidget()
        self._line.setCursor(Qt.CursorShape.PointingHandCursor)
        line = QHBoxLayout(self._line)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(0)
        self.name = QLabel()
        self.name.setObjectName("SheetName")
        self.name.setFont(ui_font(14))
        self.value = QLabel()
        self.value.setObjectName("SheetValueMono" if mono_value else "SheetValue")
        self.value.setFont(ui_font(13, 400, mono=mono_value))
        self.value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        line.addWidget(self.name)
        line.addWidget(_Leader(), 1)
        line.addWidget(self.value)
        outer.addWidget(self._line)
        self.details = QWidget()
        self.details_layout = QVBoxLayout(self.details)
        self.details_layout.setContentsMargins(0, 0, 0, 8)
        self.details_layout.setSpacing(10)
        self.details.setVisible(False)
        outer.addWidget(self.details)
        self._line.installEventFilter(self)

    def is_open(self) -> bool:
        return self._open

    def set_open(self, open_: bool) -> None:
        self._open = open_
        self.details.setVisible(open_ and self.details_layout.count() > 0)
        self._mark()

    def _mark(self) -> None:
        lit = self._open or self._hover
        self.name.setProperty("lit", "true" if lit else "false")
        for label in (self.name, self.value):
            label.style().unpolish(label)
            label.style().polish(label)

    def eventFilter(self, obj, e):  # noqa: N802 - Qt API
        kind = e.type()
        if kind == e.Type.Enter:
            self._hover = True
            self._mark()
        elif kind == e.Type.Leave:
            self._hover = False
            self._mark()
        elif kind == e.Type.MouseButtonRelease:
            self.clicked.emit()
            return True
        return False


class _Word(QWidget):
    """A clickable word of a Choice: ink when chosen, faint otherwise."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Kept apart: the window stylesheet replaces the family of setFont.
        self._font = ui_font(13)
        self._text = ""
        self.chosen = False
        self._hover = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setText(self, text: str) -> None:  # noqa: N802 - Qt API
        self._text = text
        self.setAccessibleName(text)
        self.updateGeometry()
        self.update()

    def text(self) -> str:
        return self._text

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return QSize(QFontMetrics(self._font).horizontalAdvance(self._text) + 2, 22)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt API
        return self.sizeHint()

    def enterEvent(self, e):  # noqa: N802 - Qt API
        self._hover = True
        self.update()

    def leaveEvent(self, e):  # noqa: N802 - Qt API
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, e):  # noqa: N802 - Qt API
        self.clicked.emit()

    def keyPressEvent(self, e):  # noqa: N802 - Qt API
        if e.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clicked.emit()
        else:
            super().keyPressEvent(e)

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        role = "ink" if self.chosen else ("ink-muted" if self._hover else "ink-faint")
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setFont(self._font)
        p.setPen(parse_color(c[role]))
        # Same baseline as the names of a sheet (15px).
        p.drawText(QPointF(1, 15), self._text)
        if self.hasFocus():
            p.setPen(QPen(parse_color(c["accent"]), 1))
            p.drawLine(QPointF(1, 19.5), QPointF(self.width() - 1, 19.5))
        p.end()


class Choice(QWidget):
    """A few words, one of them chosen (in ink, the others faint).

    Signals:
        chosen(str): The value of the word clicked.
    """

    chosen = Signal(str)

    def __init__(self, values: Iterable[str], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self._words: List[Tuple[str, _Word]] = []
        self._value: Optional[str] = None
        for value in values:
            word = _Word()
            word.clicked.connect(lambda v=value: self._click(v))
            layout.addWidget(word)
            self._words.append((value, word))

    def set_texts(self, texts: Iterable[str]) -> None:
        for (_value, word), text in zip(self._words, texts):
            word.setText(text)

    def value(self) -> Optional[str]:
        return self._value

    def set_value(self, value: Optional[str]) -> None:
        self._value = value
        for v, word in self._words:
            word.chosen = v == value
            word.setAccessibleDescription("selected" if v == value else "")
            word.update()

    def _click(self, value: str) -> None:
        if value != self._value:
            self.set_value(value)
            self.chosen.emit(value)


class ChoiceLine(QWidget):
    """A line of a sheet whose value is a Choice: name ....... a  b  c."""

    def __init__(self, values: Iterable[str], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.name = QLabel()
        self.name.setObjectName("SheetName")
        self.name.setFont(ui_font(14))
        self.choice = Choice(values)
        layout.addWidget(self.name)
        layout.addWidget(_Leader(), 1)
        layout.addWidget(self.choice)


class VariableChip(QLabel):
    """A variable of a name model, such as {title}, in faint mono text:
    click to insert it.

    Signals:
        picked(str): The variable, with its braces.
    """

    picked = Signal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        # Kept apart: the window stylesheet replaces the family of setFont.
        self._font = ui_font(12, 400, mono=True)
        self.setFont(self._font)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hover = False

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt API
        width = QFontMetrics(self._font).horizontalAdvance(self.text())
        return QSize(width + 2, 18)

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
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setFont(self._font)
        p.setPen(parse_color(c["ink"] if self._hover else c["ink-faint"]))
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
        #{root} QLabel#SheetName {{ color: {c["ink-muted"]}; font-size: 14px; }}
        #{root} QLabel#SheetName[lit="true"] {{ color: {c["ink"]}; }}
        #{root} QLabel#SheetValue {{ color: {c["ink"]}; font-size: 13px; }}
        #{root} QLabel#SheetValueMono {{
            color: {c["ink"]}; font-family: '{mono}'; font-size: 13px;
        }}
        #{root} QLabel#SettingPath {{
            color: {c["ink"]}; font-family: '{mono}'; font-size: 13px;
        }}
        #{root} QLabel#SettingPath[empty="true"] {{ color: {c["ink-faint"]}; }}
        #{root} QLabel[tone="ok"], #{root} QLabel#RowSubtitle[tone="ok"],
        #{root} QLabel#SettingHint[tone="ok"],
        #{root} QLabel#SheetValue[tone="ok"] {{ color: {c["ink-muted"]}; }}
        #{root} QLabel[tone="warn"], #{root} QLabel#RowSubtitle[tone="warn"],
        #{root} QLabel#SettingHint[tone="warn"],
        #{root} QLabel#SheetValue[tone="warn"] {{ color: {c["caution"]}; }}
        #{root} QLabel[tone="error"], #{root} QLabel#RowSubtitle[tone="error"],
        #{root} QLabel#SettingHint[tone="error"],
        #{root} QLabel#SheetValue[tone="error"] {{ color: {c["danger"]}; }}
        #{root} QLabel[tone="info"], #{root} QLabel#RowSubtitle[tone="info"],
        #{root} QLabel#SettingHint[tone="info"],
        #{root} QLabel#SheetValue[tone="info"] {{ color: {c["ink-faint"]}; }}
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
