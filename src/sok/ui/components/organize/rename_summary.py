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
"""The right column of a media page once a rename is over.

It takes the place of the scene: a fan of the covers sorted, a dotted sheet
(sorted, time, size moved, left in place, destination), the keys to open
the folder and to undo the rename, and a short note. The list on the left
shows each file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap, QRadialGradient
from PySide6.QtWidgets import QBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from sok.ui.components.base import KeyButton, parse_color
from sok.ui.components.media_visual import (
    dominant_color,
    draw_fan,
    rounded,
    standin_colors,
    standin_pixmap,
)
from sok.ui.components.scene import _Sheet, paint_light
from sok.ui.motion import STAGGER, cascade, rise
from sok.ui.responsive import LOW_HEIGHT
from sok.ui.theme import Theme, ui_font


def _palette(widget: QWidget) -> dict[str, str]:
    return getattr(widget.window(), "c", None) or Theme.DARK


@dataclass
class SummaryData:
    """What the summary shows.

    Attributes:
        covers: Up to three (cover, title) of the items sorted.
        square: The covers are square (albums).
        fields: (label, value) rows of the dotted sheet.
        tones: Palette color of the value of some labels ("caution" for
            the files left in place).
        can_undo: Show the undo key.
    """

    covers: List[Tuple[Optional[QPixmap], str]] = field(default_factory=list)
    square: bool = False
    fields: List[Tuple[str, str]] = field(default_factory=list)
    tones: Dict[str, str] = field(default_factory=dict)
    can_undo: bool = True


class _Fan(QWidget):
    """Three covers fanned out on the floor."""

    STEP = 66
    RADIUS = 12

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(270)
        self._covers: List[Tuple[Optional[QPixmap], str]] = []
        self._square = False
        # Covers whose picture is still travelling to the fan (motion.fly).
        self.hidden: Set[int] = set()

    def set_covers(self, covers, square: bool) -> None:
        self._covers = covers
        self._square = square
        self.update()

    def _size(self) -> Tuple[int, int]:
        return (180, 180) if self._square else (160, 240)

    def slot_rect(self, index: int) -> QRectF:
        """Rectangle of a cover in this widget."""
        w, h = self._size()
        span = w + self.STEP * (len(self._covers) - 1)
        return QRectF((self.width() - span) / 2 + index * self.STEP, 0, w, h)

    def cover_pixmap(self, index: int) -> QPixmap:
        """A cover as the fan draws it."""
        w, h = self._size()
        pixmap, title = self._covers[index]
        ratio = self.devicePixelRatioF()
        source = pixmap or standin_pixmap(title, "", w, h, ratio, text=False)
        return rounded(source, w, h, self.RADIUS)

    def set_hidden(self, index: int, hidden: bool) -> None:
        if hidden:
            self.hidden.add(index)
        else:
            self.hidden.discard(index)
        self.update()

    def object_rect(self) -> QRectF:
        w, h = self._size()
        return QRectF((self.width() - w) / 2, 0, w, h)

    def paintEvent(self, e):  # noqa: N802 - Qt API
        if not self._covers:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self._size()
        step = self.STEP
        span = w + step * (len(self._covers) - 1)
        x = (self.width() - span) / 2
        floor_y = h + 18
        floor = QRadialGradient(QPointF(self.width() / 2, floor_y), span / 2)
        floor.setColorAt(0, QColor(0, 0, 0, 200))
        floor.setColorAt(1, QColor(0, 0, 0, 0))
        p.save()
        p.translate(self.width() / 2, floor_y)
        p.scale(1, 20 / span)
        p.translate(-self.width() / 2, -floor_y)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(floor)
        p.drawEllipse(QPointF(self.width() / 2, floor_y), span / 2, span / 2)
        p.restore()
        draw_fan(
            p,
            self._covers,
            x,
            0,
            (w, h),
            step,
            self.RADIUS,
            self.devicePixelRatioF(),
            skip=self.hidden,
        )
        p.end()


class RenameSummary(QWidget):
    """The rename that just ended: covers, figures, open and undo.

    Signals:
        open_clicked: Open the destination folder.
        undo_clicked: Undo the whole rename.
    """

    open_clicked = Signal()
    undo_clicked = Signal()
    # The light or the covers moved: the page repaints what spills out.
    light_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor(128, 128, 128)
        # True while the window paints the light (see Scene.inline_light).
        self.inline_light = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 64, 44, 36)
        layout.setSpacing(0)
        self._fan = _Fan()
        layout.addWidget(self._fan)
        layout.addSpacing(28)
        self._sheet = _Sheet()
        layout.addWidget(self._sheet)
        layout.addSpacing(28)
        # Side by side, or one above the other in a narrow column.
        keys = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._keys = keys
        keys.setSpacing(10)
        keys.addStretch()
        self.open_btn = KeyButton("", primary=True)
        self.open_btn.clicked.connect(self.open_clicked.emit)
        self.undo_btn = KeyButton("")
        self.undo_btn.clicked.connect(self.undo_clicked.emit)
        keys.addWidget(self.open_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        keys.addWidget(self.undo_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        keys.addStretch()
        layout.addLayout(keys)
        layout.addSpacing(16)
        self.note = QLabel()
        self.note.setFont(ui_font(13))
        self.note.setWordWrap(True)
        self.note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.note)
        layout.addStretch()
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def arrive(self, delay: int = 0) -> None:
        """Come in, once per rename: the covers land on the fan (moved by
        the page, see cover_slot()), then the figures, the keys and the
        note come in one after the other."""
        rise(self._fan, delay + 120)
        after = self._sheet.reveal(delay + 260)
        cascade([self.open_btn, self.undo_btn], after, 0)
        rise(self.note, after + STAGGER)

    def cover_count(self) -> int:
        """Number of covers on the fan (0 when it is not shown)."""
        return len(self._fan._covers) if not self._fan.isHidden() else 0

    def cover_slot(self, index: int) -> Tuple[QPixmap, QRectF]:
        """A cover as drawn and its rectangle in this widget."""
        rect = self._fan.slot_rect(index).translated(QPointF(self._fan.pos()))
        return self._fan.cover_pixmap(index), rect

    def set_cover_hidden(self, index: int, hidden: bool) -> None:
        """Leave a cover out while its picture travels to the fan."""
        self._fan.set_hidden(index, hidden)

    def paint_light_into(self, p: QPainter, offset: QPointF, area: QRectF) -> None:
        """Paint this light in another widget, this one at offset there."""
        if not self._fan.isVisible():
            return
        obj = self._fan.object_rect().translated(QPointF(self._fan.pos()) + offset)
        rect = QRectF(offset, QRectF(self.rect()).size())
        paint_light(p, rect, self._color, obj, area)

    def resizeEvent(self, e):  # noqa: N802 - Qt API
        super().resizeEvent(e)
        self.light_changed.emit()
        self._fan.setVisible(bool(self._fan._covers) and self._room())
        self._keys.setDirection(
            QBoxLayout.Direction.TopToBottom
            if self.width() < 440
            else QBoxLayout.Direction.LeftToRight
        )

    def _room(self) -> bool:
        """Room for the covers above the figures (the window is not low)."""
        window = self.window()
        return window is None or window.height() >= LOW_HEIGHT + 120

    def show_data(self, data: SummaryData) -> None:
        self._fan.set_covers(data.covers, data.square)
        self._fan.setVisible(bool(data.covers) and self._room())
        self._sheet.set_fields(data.fields, data.tones)
        self.undo_btn.setVisible(data.can_undo)
        self.note.setVisible(data.can_undo)
        self.light_changed.emit()
        if data.covers:
            first, title = data.covers[0]
            self._color = standin_colors(title)[0]
            if first is not None:
                self._color = dominant_color(first)
        self.update()

    def _restyle(self) -> None:
        c = _palette(self)
        self.note.setStyleSheet(f"color: {c['ink-muted']}; background: transparent;")

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            self._restyle()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        if not self.inline_light:
            p.fillRect(rect, parse_color(c["bg"]))
            self.paint_light_into(p, QPointF(0, 0), rect)
        p.setPen(parse_color(c["line"]))
        p.drawLine(QPointF(0.5, 0), QPointF(0.5, rect.height()))
        p.end()
