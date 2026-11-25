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
"""The scene when S.O.K needs an answer: search again and pick the result.

Shown in place of the scene for an item to pick, an item not found, or after
"This is not it": a search field filled with the query, the results as small
rows (thumbnail, title, detail) and a Cancel key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sok.ui.components.base import KeyButton, parse_color
from sok.ui.components.media_visual import rounded, standin_pixmap
from sok.ui.components.search import load_poster
from sok.ui.motion import cascade
from sok.ui.theme import Theme, ui_font
from sok.ui.tokens import RADIUS


@dataclass
class Choice:
    """A result offered in the pick list.

    Attributes:
        title: Title of the result.
        detail: Year, author or artist ("" for none).
        image_url: Thumbnail to load, or None for the stand-in.
        current: This result is the one chosen now.
    """

    title: str
    detail: str = ""
    image_url: Optional[str] = None
    current: bool = False


def _palette(widget: QWidget) -> dict[str, str]:
    return getattr(widget.window(), "c", None) or Theme.DARK


class _ChoiceRow(QWidget):
    """A result: thumbnail, title and detail. Click to choose it."""

    clicked = Signal()
    HEIGHT = 56
    THUMB = QSize(28, 42)

    def __init__(self, choice: Choice, parent=None):
        super().__init__(parent)
        self._choice = choice
        self._hovered = False
        self._thumb: Optional[QPixmap] = None
        # True while a picture of the thumbnail travels (motion.fly).
        self.thumb_hidden = False
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        if choice.image_url:
            load_poster(choice.image_url, 56, 84, self, self._on_image)

    @property
    def current(self) -> bool:
        return self._choice.current

    def thumb_rect(self) -> QRectF:
        """Rectangle of the thumbnail in this row."""
        top = (self.HEIGHT - self.THUMB.height()) // 2
        return QRectF(10, top, self.THUMB.width(), self.THUMB.height())

    def set_thumb_hidden(self, hidden: bool) -> None:
        self.thumb_hidden = hidden
        self.update()

    def _on_image(self, pixmap: QPixmap) -> None:
        self._thumb = rounded(pixmap, self.THUMB.width(), self.THUMB.height(), 4)
        self.update()

    def enterEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = True
        self.update()

    def leaveEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = False
        self.update()

    def mouseReleaseEvent(self, e):  # noqa: N802 - Qt API
        if e.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            e.position().toPoint()
        ):
            self.clicked.emit()

    def keyPressEvent(self, e):  # noqa: N802 - Qt API
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
        else:
            super().keyPressEvent(e)

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect())
        if self._hovered or self._choice.current or self.hasFocus():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(parse_color(c["surface-raised"]))
            p.drawRoundedRect(box, RADIUS["key-sm"], RADIUS["key-sm"])
        if self._thumb is None:
            self._thumb = rounded(
                standin_pixmap(
                    self._choice.title, "", 28, 42, self.devicePixelRatioF()
                ),
                28,
                42,
                4,
            )
        if not self.thumb_hidden:
            p.drawPixmap(10, (self.HEIGHT - 42) // 2, self._thumb)
        left = 10 + 28 + 14
        width = int(self.width() - left - 12)
        title_font, detail_font = ui_font(15, 600), ui_font(12, 400, mono=True)
        p.setFont(title_font)
        p.setPen(parse_color(c["ink"]))
        p.drawText(
            left,
            25,
            QFontMetrics(title_font).elidedText(
                self._choice.title, Qt.TextElideMode.ElideRight, width
            ),
        )
        if self._choice.detail:
            p.setFont(detail_font)
            p.setPen(parse_color(c["ink-muted"]))
            p.drawText(
                left,
                43,
                QFontMetrics(detail_font).elidedText(
                    self._choice.detail, Qt.TextElideMode.ElideRight, width
                ),
            )
        if self._choice.current:
            p.setPen(QPen(parse_color(c["accent"]), 2))
            p.drawLine(self.width() - 14, 18, self.width() - 14, self.HEIGHT - 18)
        p.end()


class PickPanel(QWidget):
    """Search field, results to pick from, and Cancel.

    Signals:
        search(str): Search again with this text.
        chosen(int): Index of the chosen result.
        cancelled: Back to the scene without changing anything.
    """

    search = Signal(str)
    chosen = Signal(int)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 56, 44, 36)
        layout.setSpacing(18)

        self._title = QLabel()
        title_font = ui_font(30, 650)
        title_font.setLetterSpacing(title_font.SpacingType.AbsoluteSpacing, -1.05)
        self._title.setFont(title_font)
        self._title.setWordWrap(True)
        layout.addWidget(self._title)

        self._was = QLabel()
        self._was.setFont(ui_font(12, 400, mono=True))
        self._was.setWordWrap(True)
        layout.addWidget(self._was)

        self._field = QLineEdit()
        self._field.setObjectName("PickSearch")
        self._field.setFont(ui_font(15))
        self._field.setMinimumHeight(40)
        self._field.returnPressed.connect(
            lambda: self.search.emit(self._field.text().strip())
        )
        layout.addWidget(self._field)

        self._status = QLabel()
        self._status.setFont(ui_font(13))
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        scroll = QScrollArea()
        self._scroll = scroll
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Only the viewport: a stylesheet on the scroll area would draw its
        # scroll bar with Qt instead of the system (arrows on macOS).
        scroll.viewport().setStyleSheet("background: transparent;")
        inner = QWidget()
        inner.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._list = QVBoxLayout(inner)
        self._list.setContentsMargins(0, 0, 0, 0)
        self._list.setSpacing(2)
        self._list.addStretch()
        self._rows: List[_ChoiceRow] = []
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        self._cancel = KeyButton("", small=True)
        self._cancel.clicked.connect(self.cancelled.emit)
        actions.addWidget(self._cancel)
        actions.addStretch()
        layout.addLayout(actions)
        self._restyle()

    def set_texts(self, title: str, placeholder: str, cancel: str) -> None:
        self._title.setText(title)
        self._field.setPlaceholderText(placeholder)
        self._cancel.setText(cancel)

    def show_item(
        self, was: str, query: str, choices: List[Choice], status: str = ""
    ) -> None:
        """Fill the panel for an item.

        Args:
            was: "was <original name>", under the title.
            query: Text of the search field.
            choices: Results to pick from.
            status: Sentence above the results ("Searching…", "Nothing
                found for…"), or "".
        """
        self._was.setText(was)
        self._field.setText(query)
        self._status.setText(status)
        self._status.setVisible(bool(status))
        self._rows = []
        while self._list.count() > 1:
            item = self._list.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()
        for index, choice in enumerate(choices):
            row = _ChoiceRow(choice)
            row.clicked.connect(lambda i=index: self.chosen.emit(i))
            self._list.insertWidget(self._list.count() - 1, row)
            self._rows.append(row)
        self._restyle()

    def current_index(self) -> Optional[int]:
        """Index of the result chosen now, if there is one."""
        for index, row in enumerate(self._rows):
            if row.current:
                return index
        return None

    def thumb(self, index: int) -> Optional[Tuple[QWidget, QRectF]]:
        """The row of a result and the rectangle of its thumbnail in it, if
        the row is in view."""
        if not 0 <= index < len(self._rows):
            return None
        row = self._rows[index]
        viewport = self._scroll.viewport()
        top = row.mapTo(viewport, QPoint(0, 0)).y()
        if top < 0 or top + row.height() > viewport.height():
            return None
        return row, row.thumb_rect()

    def set_thumb_hidden(self, index: int, hidden: bool) -> None:
        if 0 <= index < len(self._rows):
            self._rows[index].set_thumb_hidden(hidden)

    def arrive(self, delay: int = 0) -> None:
        """Bring the title, the field, the results and Cancel in, one
        after the other."""
        cascade(
            [
                self._title,
                self._was,
                self._field,
                self._status,
                *self._rows,
                self._cancel,
            ],
            delay,
            40,
        )

    def focus_search(self) -> None:
        self._field.setFocus()
        self._field.selectAll()

    def _restyle(self) -> None:
        c = _palette(self)
        self._title.setStyleSheet(f"color: {c['ink']}; background: transparent;")
        self._was.setStyleSheet(
            f"color: {c['ink-faint']}; background: transparent;"
            f" font-family: '{Theme.MONO}';"
        )
        self._status.setStyleSheet(f"color: {c['ink-muted']}; background: transparent;")
        self._field.setStyleSheet(
            f"QLineEdit {{ background: {c['surface-raised']}; color: {c['ink']};"
            f" border: 1px solid {c['line-strong']}; border-radius: {RADIUS['key-sm']}px;"
            f" padding: 0 12px; }}"
            f" QLineEdit:focus {{ border-color: {c['accent']}; }}"
        )

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            self._restyle()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        p.fillRect(self.rect(), parse_color(c["bg"]))
        p.setPen(QPen(parse_color(c["line"]), 1))
        p.drawLine(0, 0, 0, self.height())
        p.end()
