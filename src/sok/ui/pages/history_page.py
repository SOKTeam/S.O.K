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
"""History page: every rename, by day, and the one selected on the scene.

The list groups the renames by day (today, yesterday, earlier this month)
and folds the older months into one row each. A row shows the time, a fan
of the covers, "17 movies sorted", where from and where to, its state and
its size. The scene shows the rename selected: its details, the files with
what each one was, and the keys to undo it or open its folder.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QDate, QLocale, QPointF, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFontMetrics,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sok.config import get_config_manager
from sok.core.history import COPY, LINK, Move, Operation, get_history
from sok.ui import message_box
from sok.ui.components.base import KeyButton, parse_color
from sok.ui.components.media_visual import draw_fan, standin_colors
from sok.ui.components.scene import _Sheet
from sok.ui.controllers.undo import undo_operation
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.i18n import tr, trn
from sok.ui.pages.batch_page import KIND_TEXTS, display_path, human_size
from sok.ui.pages.home_page import when_text
from sok.ui.responsive import SidePanel, fit_display, side_width
from sok.ui.theme import Theme, ui_font

# The kind of texts of the page an operation was made on, by its kind.
OPERATION_KINDS = {
    "movie": "movies",
    "tv_series": "series",
    "episode": "series",
    "album": "music",
    "track": "music",
    "book": "books",
    "game": "games",
}


def _palette(widget: QWidget) -> Dict[str, str]:
    return getattr(widget.window(), "c", None) or Theme.DARK


def main_moves(operation: Operation) -> List[Move]:
    """The moves of the files themselves, without the subtitles that followed."""
    return [m for m in operation.moves if m.follows is None] or list(operation.moves)


def operation_title(operation: Operation) -> str:
    """ "17 movies sorted", in the words of the page it was made on."""
    count = len(main_moves(operation))
    kind = OPERATION_KINDS.get(operation.kind)
    if kind is None:
        return trn("history_files_sorted", count, "{n} file sorted", "{n} files sorted")
    key, one, other = KIND_TEXTS[kind]["done"]
    return trn(key, count, one, other).rstrip(".")


def operation_moment(operation: Operation) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(operation.date)
    except ValueError:
        return None


def common_parent(paths: List[str]) -> Optional[Path]:
    """The folder holding all the paths, or None."""
    if not paths:
        return None
    try:
        return Path(os.path.commonpath([str(Path(p).parent) for p in paths]))
    except ValueError:
        return None


def operation_size(operation: Operation) -> int:
    """Bytes of the files where they are now."""
    total = 0
    for move in operation.moves:
        path = move.source if move.undone else move.target
        try:
            total += os.path.getsize(path)
        except OSError:
            pass
    return total


def operation_state(operation: Operation) -> Tuple[str, str]:
    """(text, palette color) of the tag of a row, or ("", "")."""
    if operation.undone:
        return tr("history_undone", "Undone"), "ink-muted"
    if operation.partly_undone:
        return tr("history_partly_undone", "Partly undone"), "ink-muted"
    gone = sum(
        1
        for m in main_moves(operation)
        if not m.undone and not os.path.exists(m.target)
    )
    if gone:
        return (
            trn(
                "history_moved_since",
                gone,
                "{n} file moved since",
                "{n} files moved since",
            ),
            "caution",
        )
    return "", ""


def operation_covers(
    operation: Operation, count: int = 3
) -> List[Tuple[Optional[QPixmap], str]]:
    """The posters saved by the rename, else stand-ins named after its files."""
    covers: List[Tuple[Optional[QPixmap], str]] = []
    for art in operation.artwork:
        if len(covers) >= count:
            break
        if not art.removed and os.path.exists(art.path):
            pixmap = QPixmap(art.path)
            if not pixmap.isNull():
                covers.append((pixmap, Path(art.path).stem))
    for move in main_moves(operation):
        if len(covers) >= count:
            break
        covers.append((None, Path(move.target).parent.name))
    return covers


def month_name(day: date) -> str:
    locale = QLocale(get_config_manager().get("language", "en"))
    return locale.standaloneMonthName(day.month, QLocale.FormatType.LongFormat)


def short_day(day: date) -> str:
    """ "19 nov." in the language of the interface."""
    locale = QLocale(get_config_manager().get("language", "en"))
    return f"{day.day} {locale.monthName(day.month, QLocale.FormatType.ShortFormat)}"


class OperationRow(QWidget):
    """A rename in the list: time, covers, title, where, state, size.

    Signals:
        clicked: The row was clicked.
    """

    clicked = Signal()
    HEIGHT = 64

    def __init__(self, operation: Operation, time_text: str):
        super().__init__()
        self.operation = operation
        self._time = time_text
        self._selected = False
        self._hovered = False
        self._covers = operation_covers(operation)
        size = operation_size(operation)
        self._size = human_size(size) if size else ""
        moves = main_moves(operation)
        source = common_parent([m.source for m in moves])
        target = common_parent([m.target for m in moves])
        parts = []
        if source is not None:
            parts.append(
                tr("history_from", "From {0}").format(display_path(source, 36))
            )
        if target is not None:
            parts.append(tr("history_to", "to {0}").format(display_path(target, 36)))
        self._where = " · ".join(parts)
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def enterEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = True
        self.update()

    def leaveEvent(self, e):  # noqa: N802 - Qt API
        self._hovered = False
        self.update()

    def mouseReleaseEvent(self, e):  # noqa: N802 - Qt API
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        op = self.operation
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect())
        if self._selected or self._hovered:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(parse_color(c["surface-raised"]))
            if not self._selected:
                p.setOpacity(0.5)
            p.drawRoundedRect(box, 14, 14)
            p.setOpacity(1)
            if self._selected:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(parse_color(c["line"]), 1))
                p.drawRoundedRect(box.adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)
        mono = ui_font(13, 400, mono=True, tabular=True)
        p.setFont(mono)
        p.setPen(parse_color(c["ink-faint"]))
        p.drawText(
            QRectF(14, 0, 52, self.height()), Qt.AlignmentFlag.AlignVCenter, self._time
        )
        if op.undone:
            p.setOpacity(0.45)
        draw_fan(
            p,
            self._covers,
            14 + 52 + 16,
            (self.height() - 39) / 2,
            (26, 39),
            10,
            4,
            self.devicePixelRatioF(),
        )
        p.setOpacity(1)

        right = self.width() - 14
        size_width = 70
        p.setFont(mono)
        p.setPen(parse_color(c["ink-faint"]))
        p.drawText(
            QRectF(right - size_width, 0, size_width, self.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
            self._size,
        )
        right -= size_width + 16
        state, tone = operation_state(op)
        if state:
            tag_font = ui_font(11, 400, mono=True)
            width = QFontMetrics(tag_font).horizontalAdvance(state) + 16
            tag = QRectF(right - width, (self.height() - 20) / 2, width, 20)
            p.setPen(QPen(parse_color(c["line-strong"]), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(tag.adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)
            p.setFont(tag_font)
            p.setPen(parse_color(c[tone]))
            p.drawText(tag, Qt.AlignmentFlag.AlignCenter, state)
            right = tag.left() - 16

        left = 14 + 52 + 16 + 46 + 16
        width = int(right - left)
        title_font = ui_font(16, 600)
        title_font.setLetterSpacing(title_font.SpacingType.AbsoluteSpacing, -0.32)
        p.setFont(title_font)
        p.setPen(parse_color(c["ink-faint"] if op.undone else c["ink"]))
        p.drawText(
            left,
            int(self.height() / 2 - 2),
            QFontMetrics(title_font).elidedText(
                operation_title(op), Qt.TextElideMode.ElideRight, width
            ),
        )
        small = ui_font(13)
        p.setFont(small)
        p.setPen(parse_color(c["ink-muted"]))
        p.drawText(
            left,
            int(self.height() / 2 + 16),
            QFontMetrics(small).elidedText(
                self._where, Qt.TextElideMode.ElideMiddle, width
            ),
        )
        p.end()


class MonthRow(QWidget):
    """An older month folded into one row, with a key to show it."""

    show_clicked = Signal()

    def __init__(self, label: str, text: str):
        super().__init__()
        self.setFixedHeight(52)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(16)
        self._label = QLabel(label)
        self._label.setFixedWidth(52)
        self._label.setFont(ui_font(13, 400, mono=True))
        self._text = QLabel(text)
        self._text.setFont(ui_font(15))
        self.button = KeyButton(tr("history_show", "Show"), small=True)
        self.button.clicked.connect(self.show_clicked.emit)
        layout.addWidget(self._label)
        layout.addWidget(self._text, 1)
        layout.addWidget(self.button)

    def restyle(self) -> None:
        c = _palette(self)
        self._label.setStyleSheet(
            f"color: {c['ink-faint']}; font-family: '{Theme.MONO}'; background: transparent;"
        )
        self._text.setStyleSheet(f"color: {c['ink-muted']}; background: transparent;")


class _Fan(QWidget):
    """Three covers on the scene, with their shadow on the floor."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(250)
        self._covers: List[Tuple[Optional[QPixmap], str]] = []
        self._faded = False

    def set_covers(self, covers, faded: bool) -> None:
        self._covers = covers
        self._faded = faded
        self.update()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        if not self._covers:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, step = 140, 210, 70
        span = w + step * (len(self._covers) - 1)
        x = (self.width() - span) / 2
        floor = QRadialGradient(QPointF(self.width() / 2, h + 18), span / 2)
        floor.setColorAt(0, QColor(0, 0, 0, 200))
        floor.setColorAt(1, QColor(0, 0, 0, 0))
        p.save()
        p.translate(self.width() / 2, h + 18)
        p.scale(1, 18 / span)
        p.translate(-self.width() / 2, -(h + 18))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(floor)
        p.drawEllipse(QPointF(self.width() / 2, h + 18), span / 2, span / 2)
        p.restore()
        if self._faded:
            p.setOpacity(0.45)
        draw_fan(p, self._covers, x, 0, (w, h), step, 14, self.devicePixelRatioF())
        p.end()


class _FileLine(QWidget):
    """A file of the rename: its new path, what it was, and a key to put it
    back."""

    def __init__(self, new: str, was: str, done: bool):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(10)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.new = QLabel(new)
        self.new.setFont(ui_font(12, 400, mono=True))
        self.was = QLabel(was)
        self.was.setFont(ui_font(11, 400, mono=True))
        for label in (self.new, self.was):
            label.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
            )
            texts.addWidget(label)
        layout.addLayout(texts, 1)
        self.button = KeyButton("↺", small=True)
        self.button.setToolTip(tr("history_undo_file", "Put this file back"))
        self.button.setVisible(not done)
        layout.addWidget(self.button)
        self._done = done

    def restyle(self) -> None:
        c = _palette(self)
        mono = f"font-family: '{Theme.MONO}'; background: transparent;"
        self.new.setStyleSheet(
            f"color: {c['ink-faint' if self._done else 'ink']}; {mono}"
        )
        self.was.setStyleSheet(f"color: {c['ink-faint']}; {mono}")


class HistoryScene(QWidget):
    """The rename selected: covers, title, details, files and keys.

    Signals:
        undo_clicked: Undo the whole rename.
        undo_file(int): Put one file back (index in operation.moves).
        open_clicked: Open the folder the files went to.
    """

    undo_clicked = Signal()
    undo_file = Signal(int)
    open_clicked = Signal()
    # The light moved: the page repaints what spills out.
    light_changed = Signal()

    def __init__(self):
        super().__init__()
        # True while the window paints the light (see Scene.inline_light).
        self.inline_light = False
        self._color = QColor(128, 128, 128)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 60, 44, 36)
        layout.setSpacing(0)
        self._fan = _Fan()
        layout.addWidget(self._fan)
        layout.addSpacing(32)
        self._when = QLabel()
        label = ui_font(11, 600)
        label.setLetterSpacing(label.SpacingType.AbsoluteSpacing, 0.88)
        label.setCapitalization(label.Capitalization.AllUppercase)
        self._when.setFont(label)
        self._when.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._when)
        layout.addSpacing(4)
        self._title = QLabel()
        title = ui_font(30, 650)
        title.setLetterSpacing(title.SpacingType.AbsoluteSpacing, -1.05)
        self._title.setFont(title)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setWordWrap(True)
        layout.addWidget(self._title)
        layout.addSpacing(22)
        self._sheet = _Sheet()
        layout.addWidget(self._sheet)
        layout.addSpacing(12)
        self._files = QVBoxLayout()
        self._files.setSpacing(0)
        layout.addLayout(self._files)
        self._more = QLabel()
        self._more.setFont(ui_font(13))
        layout.addWidget(self._more)
        layout.addSpacing(16)
        keys = QHBoxLayout()
        keys.addStretch()
        self.undo_btn = KeyButton("")
        self.undo_btn.clicked.connect(self.undo_clicked.emit)
        self.open_btn = KeyButton("")
        self.open_btn.clicked.connect(self.open_clicked.emit)
        keys.addWidget(self.undo_btn)
        keys.addSpacing(10)
        keys.addWidget(self.open_btn)
        keys.addStretch()
        layout.addLayout(keys)
        layout.addStretch()
        self._lines: List[_FileLine] = []

    def paint_light_into(self, p: QPainter, offset: QPointF, area: QRectF) -> None:
        """The ambient light of the covers, painted in a widget where this
        one is at offset (here, or the page under the list)."""
        center = offset + QPointF(self.width() / 2, self.height() * 0.22)
        light = QRadialGradient(center, 420)
        tint = QColor(self._color)
        tint.setAlphaF(0.11)
        light.setColorAt(0, tint)
        tint.setAlphaF(0)
        light.setColorAt(1, tint)
        p.fillRect(area, light)

    def resizeEvent(self, e):  # noqa: N802 - Qt API
        super().resizeEvent(e)
        self.light_changed.emit()

    def show_operation(self, op: Optional[Operation]) -> None:
        for line in self._lines:
            line.deleteLater()
        self._lines = []
        self.setVisible(op is not None)
        if op is None:
            return
        covers = operation_covers(op)
        self._fan.set_covers(covers, op.undone)
        self._color = (
            standin_colors(covers[0][1])[0] if covers else QColor(128, 128, 128)
        )
        moment = operation_moment(op)
        when = when_text(moment) if moment else op.date
        self._when.setText(when)
        self._title.setText(operation_title(op))
        moves = main_moves(op)
        source = common_parent([m.source for m in moves])
        target = common_parent([m.target for m in moves])
        modes = {m.mode for m in moves}
        if modes == {LINK}:
            transfer = tr("history_linked", "hard links")
        elif modes == {COPY}:
            transfer = tr("history_copied", "copied")
        else:
            transfer = tr("history_moved", "moved")
        fields = []
        if source is not None:
            fields.append((tr("history_field_from", "From"), display_path(source, 28)))
        if target is not None:
            fields.append((tr("history_field_to", "To"), display_path(target, 28)))
        fields.append((tr("history_field_transfer", "Transfer"), transfer))
        size = operation_size(op)
        if size:
            fields.append((tr("batch_size", "Size"), human_size(size)))
        self._sheet.set_fields(fields)
        for index, move in enumerate(op.moves[:4] if len(op.moves) > 5 else op.moves):
            if move.follows is not None:
                continue
            try:
                new = (
                    str(Path(move.target).relative_to(target))
                    if target
                    else Path(move.target).name
                )
            except ValueError:
                new = Path(move.target).name
            line = _FileLine(
                new, f"{tr('batch_was', 'was')} {Path(move.source).name}", move.undone
            )
            line.button.clicked.connect(lambda _=False, i=index: self.undo_file.emit(i))
            self._files.addWidget(line)
            self._lines.append(line)
        rest = len(moves) - len(self._lines)
        self._more.setText(
            trn("history_more_files", rest, "and {n} other file", "and {n} other files")
            if rest > 0
            else ""
        )
        self._more.setVisible(rest > 0)
        self.undo_btn.setText(tr("home_undo_last", "Undo this rename"))
        self.open_btn.setText(tr("batch_open_folder", "Open the folder"))
        self.undo_btn.setVisible(not op.undone)
        self._restyle()
        self.update()
        self.light_changed.emit()

    def _restyle(self) -> None:
        c = _palette(self)
        self._when.setStyleSheet(f"color: {c['ink-faint']}; background: transparent;")
        self._title.setStyleSheet(f"color: {c['ink']}; background: transparent;")
        self._more.setStyleSheet(f"color: {c['ink-muted']}; background: transparent;")
        for line in self._lines:
            line.restyle()

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            self._restyle()

    def paintEvent(self, e):  # noqa: N802 - Qt API
        c = _palette(self)
        p = QPainter(self)
        rect = QRectF(self.rect())
        if not self.inline_light:
            p.fillRect(rect, parse_color(c["bg"]))
            self.paint_light_into(p, QPointF(0, 0), rect)
        p.setPen(QPen(parse_color(c["line"]), 1))
        p.drawLine(QPointF(0.5, 0), QPointF(0.5, rect.height()))
        p.end()


class HistoryPage(QWidget):
    """Page of the history of renames, newest first."""

    # The light of the page moved: the window paints it again.
    light_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Page")
        self._runner = WorkerRunner(self)
        self._rows: List[OperationRow] = []
        self._months: List[MonthRow] = []
        self._labels: List[QLabel] = []
        self._shown_months: set[Tuple[int, int]] = set()
        self._current: Optional[str] = None
        self._build()
        self.retranslateUi()

    def _build(self) -> None:
        columns = QHBoxLayout(self)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")
        content = QWidget()
        content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        left = QVBoxLayout(content)
        left.setContentsMargins(26, 40, 40, 28)
        left.setSpacing(0)
        scroll.setWidget(content)

        head = QVBoxLayout()
        head.setContentsMargins(14, 0, 14, 0)
        head.setSpacing(10)
        self._title = QLabel()
        title = ui_font(52, 650)
        title.setLetterSpacing(title.SpacingType.AbsoluteSpacing, -2.08)
        self._title.setFont(title)
        head.addWidget(self._title)
        self._lead = QLabel()
        self._lead.setFont(ui_font(17))
        self._lead.setWordWrap(True)
        head.addWidget(self._lead)
        left.addLayout(head)
        left.addSpacing(36)
        self._list = QVBoxLayout()
        self._list.setSpacing(2)
        left.addLayout(self._list)
        left.addStretch()
        foot = QHBoxLayout()
        foot.setContentsMargins(14, 28, 14, 0)
        foot.setSpacing(16)
        self._note = QLabel()
        self._note.setFont(ui_font(13))
        self._note.setWordWrap(True)
        self._note.setTextFormat(Qt.TextFormat.RichText)
        foot.addWidget(self._note, 1)
        self._clear_btn = KeyButton("", small=True)
        self._clear_btn.set_danger(True)
        self._clear_btn.clicked.connect(self._clear)
        foot.addWidget(self._clear_btn)
        left.addLayout(foot)
        columns.addWidget(scroll, 1)

        self._scene = HistoryScene()
        self._scene.undo_clicked.connect(self._undo_all)
        self._scene.undo_file.connect(self._undo_file)
        self._scene.open_clicked.connect(self._open_folder)
        scene_scroll = QScrollArea()
        scene_scroll.setWidgetResizable(True)
        scene_scroll.setFrameShape(QFrame.Shape.NoFrame)
        scene_scroll.setFixedWidth(side_width(1440))
        scene_scroll.setWidget(self._scene)
        self._scene_scroll = scene_scroll
        # Beside the list, or over it in a narrow window.
        self._panel = SidePanel(
            self, columns, scene_scroll, lambda: tr("back_to_list", "List")
        )
        scene_scroll.viewport().setStyleSheet("background: transparent;")
        self._scene.light_changed.connect(self.light_changed.emit)
        self._panel.moved.connect(self.light_changed.emit)
        scene_scroll.verticalScrollBar().valueChanged.connect(self.light_changed)

    def light_source(self):
        """The widget whose light the window paints, or None (see
        main_window.LightColumn)."""
        if self._panel.narrow or not self._scene_scroll.isVisible():
            return None
        return self._scene

    def resizeEvent(self, e):  # noqa: N802 - Qt API
        super().resizeEvent(e)
        self._panel.fit(self.width())
        self._scene.inline_light = not self._panel.narrow
        self.light_changed.emit()
        self._scene_scroll.setFixedWidth(self._panel.column_width(self.width()))
        fit_display([self._title], self.width())

    def _restyle(self) -> None:
        c = _palette(self)
        for label, role in (
            (self._title, "ink"),
            (self._lead, "ink-muted"),
            (self._note, "ink-faint"),
        ):
            label.setStyleSheet(f"color: {c[role]}; background: transparent;")
        for label in self._labels:
            label.setStyleSheet(f"color: {c['ink-faint']}; background: transparent;")
        for month in self._months:
            month.restyle()

    def changeEvent(self, e):  # noqa: N802 - Qt API
        super().changeEvent(e)
        if e.type() in (e.Type.StyleChange, e.Type.PaletteChange):
            self._restyle()

    def retranslateUi(self) -> None:
        self._panel.retranslate()
        self._title.setText(tr("history_title", "History."))
        self._clear_btn.setText(tr("history_clear", "Clear history"))
        self.refresh()

    # ------------------------------------------------------------ Content

    def refresh(self) -> None:
        """Show the renames of the history again."""
        while self._list.count():
            item = self._list.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                widget.deleteLater()
        self._rows, self._months, self._labels = [], [], []
        operations = [op for op in get_history().operations() if op.moves]
        today = date.today()
        files = sum(len(main_moves(op)) for op in operations)
        if operations:
            first = operation_moment(operations[-1])
            since = first.date() if first else today
            locale = QLocale(get_config_manager().get("language", "en"))
            self._lead.setText(
                trn(
                    "history_lead",
                    len(operations),
                    "{n} rename since {date}, {files} files. Each one can be undone, file by file.",
                    "{n} renames since {date}, {files} files. Each one can be undone, file by file.",
                )
                .replace(
                    "{date}",
                    locale.toString(
                        QDate(since.year, since.month, since.day), "d MMMM yyyy"
                    ),
                )
                .replace("{files}", str(files))
            )
        else:
            self._lead.setText(tr("history_empty", "No renames yet."))
        self._clear_btn.setVisible(bool(operations))

        # The month of the last rename is always shown, even an old one.
        newest = operation_moment(operations[0]) if operations else None
        if newest is not None:
            self._shown_months.add((newest.year, newest.month))

        sections: Dict[str, List[Operation]] = {}
        order: List[str] = []
        months: Dict[Tuple[int, int], List[Operation]] = {}
        for op in operations:
            moment = operation_moment(op)
            day = moment.date() if moment else today
            days = (today - day).days
            if days == 0:
                key = tr("history_today", "Today")
            elif days == 1:
                key = f"{tr('history_yesterday', 'Yesterday')} · {QLocale(get_config_manager().get('language', 'en')).toString(QDate(day.year, day.month, day.day), 'dddd d MMMM')}"
            elif (day.year, day.month) == (today.year, today.month):
                key = tr("history_earlier", "Earlier in {0}").format(month_name(day))
            else:
                months.setdefault((day.year, day.month), []).append(op)
                if (day.year, day.month) not in self._shown_months:
                    continue
                key = f"{month_name(day)} {day.year}"
            if key not in sections:
                sections[key] = []
                order.append(key)
            sections[key].append(op)

        for key in order:
            label = QLabel(key)
            font = ui_font(11, 600)
            font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 0.88)
            font.setCapitalization(font.Capitalization.AllUppercase)
            label.setFont(font)
            label.setContentsMargins(14, 14, 14, 8)
            self._labels.append(label)
            self._list.addWidget(label)
            for op in sections[key]:
                moment = operation_moment(op)
                if moment and (today - moment.date()).days <= 1:
                    time_text = moment.strftime("%H:%M")
                else:
                    time_text = short_day(moment.date()) if moment else ""
                row = OperationRow(op, time_text)
                row.clicked.connect(lambda o=op: self._open_operation(o.id))
                self._rows.append(row)
                self._list.addWidget(row)
        for (year, month), ops in months.items():
            if (year, month) in self._shown_months:
                continue
            day = date(year, month, 1)
            text = (
                trn(
                    "history_month",
                    len(ops),
                    "{n} rename in {month}, {files} files",
                    "{n} renames in {month}, {files} files",
                )
                .replace("{month}", month_name(day))
                .replace("{files}", str(sum(len(main_moves(o)) for o in ops)))
            )
            month_row = MonthRow(short_day(day).split(" ", 1)[-1], text)
            month_row.show_clicked.connect(
                lambda ym=(year, month): self._show_month(ym)
            )
            self._months.append(month_row)
            self._list.addWidget(month_row)

        path = display_path(get_history().path, 60)
        self._note.setText(
            tr(
                "history_note",
                "The history is kept on this computer, in {path}. The last 100 renames are kept.",
            ).format(path=f"<span style='font-family: \"{Theme.MONO}\"'>{path}</span>")
        )
        ids = [r.operation.id for r in self._rows]
        if self._current not in ids:
            self._current = ids[0] if ids else None
        self._select(self._current)
        self._restyle()

    def _show_month(self, year_month: Tuple[int, int]) -> None:
        self._shown_months.add(year_month)
        self.refresh()

    def _open_operation(self, operation_id: str) -> None:
        """A row clicked: show it on the scene (over the list if narrow)."""
        self._select(operation_id)
        self._panel.open()

    def _select(self, operation_id: Optional[str]) -> None:
        self._current = operation_id
        current = None
        for row in self._rows:
            row.set_selected(row.operation.id == operation_id)
            if row.operation.id == operation_id:
                current = row.operation
        self._scene.show_operation(current)
        self._scene_scroll.setVisible(current is not None)

    def _operation(self) -> Optional[Operation]:
        return get_history().get(self._current) if self._current else None

    # ------------------------------------------------------------- Actions

    def undo(self, operation_id: str, index: Optional[int] = None) -> None:
        """Undo a rename, or one of its files, then show the history again."""
        undo_operation(
            self, self._runner, operation_id, index, on_done=lambda _r: self.refresh()
        )

    def _undo_file(self, index: int) -> None:
        if self._current:
            self.undo(self._current, index)

    def _undo_all(self) -> None:
        op = self._operation()
        if op is None:
            return
        left = sum(1 for m in op.moves if not m.undone)
        answer = message_box.question(
            self,
            tr("undo", "Undo"),
            tr("history_confirm_undo", "Put {0} file(s) back where they were?").format(
                left
            ),
        )
        if answer == message_box.StandardButton.Yes:
            self.undo(op.id)

    def _open_folder(self) -> None:
        op = self._operation()
        if op is None:
            return
        folder = common_parent([m.target for m in main_moves(op)])
        if folder is not None and folder.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _clear(self) -> None:
        answer = message_box.question(
            self,
            tr("history_clear", "Clear history"),
            tr(
                "history_confirm_clear",
                "Clear the history? The renames can no longer be undone. "
                "The files stay where they are.",
            ),
        )
        if answer == message_box.StandardButton.Yes:
            get_history().clear()
            self.refresh()

    def stop_workers(self) -> None:
        """Stop the undo running, if any."""
        self._runner.stop()
