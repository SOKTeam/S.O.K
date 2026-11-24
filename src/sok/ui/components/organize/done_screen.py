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
"""The screen shown after a rename: what was done, and the way back.

A sentence ("17 movies sorted."), up to three result cards, the first
changes (old name → new name) and the actions: see every change in the
history, open the folder, undo, continue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from sok.ui.components.base import KeyButton, parse_color
from sok.ui.theme import Theme, ui_font
from sok.ui.tokens import RADIUS


def _palette(widget: QWidget) -> dict[str, str]:
    return getattr(widget.window(), "c", None) or Theme.DARK


@dataclass
class StatData:
    """A result card: label, figure, context line."""

    label: str
    figure: str
    context: str = ""


@dataclass
class DoneData:
    """What the screen shows.

    Attributes:
        finished: "Done at 21:42".
        title: "17 movies sorted.".
        lead: Muted sentence under the title ("" for none).
        stats: Up to three result cards.
        changes_label: Label above the changes.
        changes: (old name, new path) of the first changes.
    """

    finished: str
    title: str
    lead: str = ""
    stats: List[StatData] = field(default_factory=list)
    changes_label: str = ""
    changes: List[Tuple[str, str]] = field(default_factory=list)


class StatCard(QWidget):
    """Label, big figure in Geist Mono, context line, on a panel."""

    def __init__(self, data: StatData, parent=None):
        super().__init__(parent)
        self._data = data
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = RADIUS["panel"]
        p.setPen(QPen(parse_color(c["line"]), 1))
        p.setBrush(parse_color(c["surface"]))
        p.drawRoundedRect(box, radius, radius)
        p.setPen(QPen(parse_color(c["highlight"]), 1))
        p.drawLine(int(radius), 1, int(self.width() - radius), 1)

        pad = 24
        label = ui_font(11, 600)
        label.setLetterSpacing(label.SpacingType.AbsoluteSpacing, 0.88)
        label.setCapitalization(label.Capitalization.AllUppercase)
        p.setFont(label)
        p.setPen(parse_color(c["ink-faint"]))
        p.drawText(pad, pad + 12, self._data.label)
        figure = ui_font(52, 500, mono=True, tabular=True)
        figure.setLetterSpacing(figure.SpacingType.AbsoluteSpacing, -1.56)
        p.setFont(figure)
        p.setPen(parse_color(c["ink"]))
        p.drawText(pad, pad + 74, self._data.figure)
        if self._data.context:
            p.setFont(ui_font(13))
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(
                QRectF(pad, pad + 86, self.width() - 2 * pad, 36),
                Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                self._data.context,
            )
        p.end()


class DoneScreen(QWidget):
    """The end of a rename.

    Signals:
        history_clicked, open_clicked, undo_clicked, continue_clicked.
    """

    history_clicked = Signal()
    open_clicked = Signal()
    undo_clicked = Signal()
    continue_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 48, 40, 32)
        layout.setSpacing(0)

        self._finished = QLabel()
        self._finished.setFont(ui_font(13, 500))
        layout.addWidget(self._finished)
        layout.addSpacing(14)

        self._title = QLabel()
        title_font = ui_font(52, 650)
        title_font.setLetterSpacing(title_font.SpacingType.AbsoluteSpacing, -2.08)
        self._title.setFont(title_font)
        self._title.setWordWrap(True)
        layout.addWidget(self._title)
        layout.addSpacing(10)

        self._lead = QLabel()
        self._lead.setFont(ui_font(17))
        self._lead.setWordWrap(True)
        layout.addWidget(self._lead)
        layout.addSpacing(32)

        self._stats = QHBoxLayout()
        self._stats.setSpacing(16)
        layout.addLayout(self._stats)
        layout.addSpacing(36)

        self._changes_label = QLabel()
        changes_font = ui_font(11, 600)
        changes_font.setLetterSpacing(changes_font.SpacingType.AbsoluteSpacing, 0.88)
        changes_font.setCapitalization(changes_font.Capitalization.AllUppercase)
        self._changes_label.setFont(changes_font)
        layout.addWidget(self._changes_label)
        layout.addSpacing(12)
        self._changes = QVBoxLayout()
        self._changes.setSpacing(10)
        layout.addLayout(self._changes)
        layout.addStretch()

        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.continue_btn = KeyButton("", primary=True)
        self.history_btn = KeyButton("")
        self.open_btn = KeyButton("")
        self.undo_btn = KeyButton("")
        self.continue_btn.clicked.connect(self.continue_clicked.emit)
        self.history_btn.clicked.connect(self.history_clicked.emit)
        self.open_btn.clicked.connect(self.open_clicked.emit)
        self.undo_btn.clicked.connect(self.undo_clicked.emit)
        for button in (
            self.continue_btn,
            self.history_btn,
            self.open_btn,
            self.undo_btn,
        ):
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)

    def show_data(self, data: DoneData) -> None:
        self._finished.setText(data.finished)
        self._title.setText(data.title)
        self._lead.setText(data.lead)
        self._lead.setVisible(bool(data.lead))
        for layout in (self._stats, self._changes):
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget() if item else None
                if widget:
                    widget.deleteLater()
        for stat in data.stats[:3]:
            self._stats.addWidget(StatCard(stat))
        self._changes_label.setText(data.changes_label)
        self._changes_label.setVisible(bool(data.changes))
        self._mono_labels: list[tuple[QLabel, str]] = []
        for old, new in data.changes:
            self._changes.addWidget(self._change_row(old, new))
        self._restyle()

    def _change_row(self, old: str, new: str) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(12)
        for text, role in ((old, "ink-faint"), ("→", "ink-faint"), (new, "ink")):
            label = QLabel(text)
            label.setFont(ui_font(13, 400, mono=True))
            self._mono_labels.append((label, role))
            line.addWidget(label)
        line.addStretch()
        return row

    def _restyle(self) -> None:
        c = _palette(self)
        for label, role in (
            (self._finished, "ink-muted"),
            (self._title, "ink"),
            (self._lead, "ink-muted"),
            (self._changes_label, "ink-faint"),
        ):
            label.setStyleSheet(f"color: {c[role]}; background: transparent;")
        for label, role in getattr(self, "_mono_labels", []):
            # The global stylesheet sets the family of every widget.
            label.setStyleSheet(
                f"color: {c[role]}; background: transparent; font-family: '{Theme.MONO}';"
            )

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            self._restyle()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        p = QPainter(self)
        p.fillRect(self.rect(), parse_color(_palette(self)["bg"]))
        p.end()
