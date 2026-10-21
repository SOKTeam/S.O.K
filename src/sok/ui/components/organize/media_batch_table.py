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
"""Table-style widget for batch renaming.

Each row is one item (a movie, a book, a game…) made of one or more source
files. It lets the user edit the search query, pick a match among the
candidates, and preview the new name. The status of a row comes from
sok.core.batch.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sok.core.batch import (
    STATUS_AMBIGUOUS,
    STATUS_MISSING,
    STATUS_READY,
    BatchMatch,
    candidate_year,
)
from sok.ui.components.base import Card
from sok.ui.components.window import StopPropagationScrollArea
from sok.ui.controllers.ui_state import set_empty_state
from sok.ui.i18n import tr
from sok.ui.platform import IS_MACOS
from sok.ui.theme import Theme, card_shadow, set_tone

logger = logging.getLogger(__name__)


STATUS_OK = STATUS_READY
STATUS_PENDING = "pending"

# Text of a candidate in the menu of a row.
Describe = Callable[[Dict[str, Any]], str]
# Splits files into items, the files of each item together.
GroupFiles = Callable[[List[Path]], List[List[Path]]]


def describe_dated(candidate: Dict[str, Any]) -> str:
    """ "Title (year)", the default text of a candidate."""
    title = candidate.get("title") or candidate.get("name") or tr("unknown", "Unknown")
    year = candidate_year(candidate)
    return f"{title} ({year})" if year else title


def one_item_per_file(files: List[Path]) -> List[List[Path]]:
    """Default grouping: every file is an item."""
    return [[f] for f in files]


class BatchRow(QWidget):
    """Single row of the batch table: one item and its search.

    Signals:
        changed: Emitted when the user changes the selected candidate or query.
        rescan_requested: Emitted when the user clicks the rescan button.
    """

    changed = Signal()
    rescan_requested = Signal(str)

    def __init__(
        self,
        files: List[Path],
        describe: Describe = describe_dated,
        query_placeholder: str = "",
        parent: Optional[QWidget] = None,
    ):
        """Initialize a row.

        Args:
            files: Source files of the item; the first one names it.
            describe: Text of a candidate in the menu.
            query_placeholder: Hint shown in the empty query field.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._files = list(files)
        self._file = self._files[0]
        self._describe = describe
        self._candidates: List[Dict[str, Any]] = []
        self._status = STATUS_PENDING
        self._new_name = ""
        self._last_emitted_query = ""

        self._rescan_timer = QTimer(self)
        self._rescan_timer.setSingleShot(True)
        self._rescan_timer.setInterval(150)
        self._rescan_timer.timeout.connect(self._emit_rescan)

        self.setFixedHeight(72)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(2)
        name = self._file.name
        if len(self._files) > 1:
            name += f"  (+{len(self._files) - 1})"
        self._original_lbl = QLabel(name)
        self._original_lbl.setToolTip("\n".join(f.name for f in self._files))
        self._original_lbl.setStyleSheet("font-size: 11px;")
        set_tone(self._original_lbl, "file")
        self._original_lbl.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._new_name_lbl = QLabel("...")
        self._new_name_lbl.setStyleSheet("font-size: 12px; font-style: italic;")
        set_tone(self._new_name_lbl, "pending")
        self._new_name_lbl.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        left.addWidget(self._original_lbl)
        left.addWidget(self._new_name_lbl)
        layout.addLayout(left, 2)

        mid = QVBoxLayout()
        mid.setSpacing(4)
        query_row = QHBoxLayout()
        query_row.setSpacing(4)
        self._query_edit = QLineEdit()
        self._query_edit.setPlaceholderText(
            query_placeholder or tr("movie_title_year", "Title (optional year)")
        )
        self._query_edit.setFixedHeight(24)
        self._query_edit.setObjectName("SettingsInput")
        self._query_edit.editingFinished.connect(self._on_query_edited)
        query_row.addWidget(self._query_edit, 1)

        self._rescan_btn = QPushButton("⟲")
        self._rescan_btn.setFixedSize(24, 24)
        self._rescan_btn.setObjectName("SmallBtn")
        self._rescan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rescan_btn.setToolTip(tr("rescan", "Re-scan"))
        self._rescan_btn.clicked.connect(self._on_rescan)
        query_row.addWidget(self._rescan_btn)

        mid.addLayout(query_row)

        self._match_combo = QComboBox()
        self._match_combo.setFixedHeight(24)
        if IS_MACOS:
            # Colors come from the main window stylesheet and follow the theme.
            self._match_combo.setObjectName("MatchCombo")
        else:
            self._match_combo.setStyleSheet(
                f"""
            QComboBox {{
                background: {Theme.DARK["input_bg"]};
                border: 1px solid {Theme.DARK["separator"]};
                border-radius: 6px;
                padding: 2px 8px;
                color: {Theme.DARK["text"]};
            }}
            QComboBox QAbstractItemView {{
                background: {Theme.DARK["dropdown_bg"]};
                border: 1px solid {Theme.DARK["separator"]};
                border-radius: 6px;
                padding: 4px;
                color: {Theme.DARK["text"]};
                outline: none;
                selection-background-color: {Theme.DARK["accent"]};
                selection-color: {Theme.DARK["accent_text"]};
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 24px;
                padding-left: 8px;
                color: {Theme.DARK["text"]};
            }}
            """
            )
        # activated, not currentIndexChanged: choosing the selected candidate
        # again confirms it.
        self._match_combo.activated.connect(self._on_match_changed)
        mid.addWidget(self._match_combo)
        layout.addLayout(mid, 3)

        self._status_lbl = QLabel("…")
        self._status_lbl.setFixedWidth(80)
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
        set_tone(self._status_lbl, "file")
        layout.addWidget(self._status_lbl)

    @property
    def file(self) -> Path:
        """Return the first source file, which names the item."""
        return self._file

    @property
    def files(self) -> List[Path]:
        """Return the source files of the item."""
        return list(self._files)

    def set_query(self, query: str, year: Optional[int] = None) -> None:
        """Set the editable query text without triggering editingFinished.

        Only the title is placed in the edit field; the year is informative
        and shown by the candidates combo. Storing year inside the query
        text would make a follow-up TMDB search miss exact-title matches.
        """
        text = (query or "").strip()
        self._query_edit.blockSignals(True)
        self._query_edit.setText(text)
        self._query_edit.setModified(False)
        self._query_edit.blockSignals(False)
        self._last_emitted_query = text

    def set_loading(self) -> None:
        """Show a transient loading state without forcing a MISSING status."""
        self._candidates = []
        self._match_combo.blockSignals(True)
        self._match_combo.clear()
        self._match_combo.addItem(tr("searching", "Searching..."), None)
        self._match_combo.setEnabled(False)
        self._match_combo.blockSignals(False)
        self.set_status(STATUS_PENDING)
        self.set_new_name("")

    def get_query(self) -> str:
        """Return the current query text."""
        return self._query_edit.text().strip()

    def set_candidates(
        self,
        candidates: List[Dict[str, Any]],
        selected: Optional[int] = None,
        status: str = STATUS_AMBIGUOUS,
    ) -> None:
        """Populate the candidates combobox.

        Args:
            candidates: List of search result dicts.
            selected: Index of the candidate to select (the first if None).
            status: Status of the row when there are candidates (see
                sok.core.batch).
        """
        self._candidates = candidates
        self._match_combo.blockSignals(True)
        self._match_combo.clear()
        if not candidates:
            self._match_combo.addItem(tr("no_match_found", "No match found"), None)
            self._match_combo.setEnabled(False)
            self.set_status(STATUS_MISSING)
        else:
            self._match_combo.setEnabled(True)
            for cand in candidates:
                self._match_combo.addItem(self._describe(cand), cand)
            self._match_combo.setCurrentIndex(selected or 0)
            self.set_status(status)
        self._match_combo.blockSignals(False)
        self.changed.emit()

    def get_selected_candidate(self) -> Optional[Dict[str, Any]]:
        """Return the currently selected candidate or None."""
        return self._match_combo.currentData()

    def set_new_name(self, name: str) -> None:
        """Update the displayed new filename preview."""
        self._new_name = name
        if name:
            self._new_name_lbl.setText(name)
            self._new_name_lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
            set_tone(self._new_name_lbl, "renamed")
        else:
            self._new_name_lbl.setText("...")
            self._new_name_lbl.setStyleSheet("font-size: 12px; font-style: italic;")
            set_tone(self._new_name_lbl, "pending")

    def set_status(self, status: str) -> None:
        """Set the visual status badge."""
        self._status = status
        if status == STATUS_OK:
            text, tone = "✓ " + tr("status_ready", "Ready"), "renamed"
        elif status == STATUS_AMBIGUOUS:
            text, tone = "⚠ " + tr("status_ambiguous", "Pick one"), "ambiguous"
        elif status == STATUS_MISSING:
            text, tone = "✗ " + tr("status_missing", "Missing"), "missing"
        else:
            text, tone = "…", "file"
        self._status_lbl.setText(text)
        set_tone(self._status_lbl, tone)

    def get_status(self) -> str:
        """Return the current status code."""
        return self._status

    def _on_query_edited(self) -> None:
        if not self._query_edit.isModified():
            return
        self._query_edit.setModified(False)
        self._rescan_timer.start()

    def _on_rescan(self) -> None:
        self._query_edit.setModified(False)
        self._rescan_timer.start()

    def _emit_rescan(self) -> None:
        q = self.get_query()
        if not q:
            return
        self._last_emitted_query = q
        self.rescan_requested.emit(q)

    def _on_match_changed(self, _idx: int) -> None:
        if self._match_combo.currentData() is not None:
            self.set_status(STATUS_OK)
        self.changed.emit()


class MediaBatchTable(QWidget):
    """Scrollable table of BatchRow widgets, one per item.

    Rows are keyed by the first file of their item.

    Signals:
        row_changed: Emitted when any row's selection or query changes.
        row_rescan_requested(Path, str): A row asks for a new search, with
            its key and the typed query.
        files_added(list): Items added by a drop or the file dialog, each a
            list of files.
    """

    row_changed = Signal()
    row_rescan_requested = Signal(object, str)
    files_added = Signal(list)

    def __init__(
        self,
        file_extensions: Optional[List[str]] = None,
        empty_hint: str = "",
        add_more_text: str = "",
        describe: Describe = describe_dated,
        query_placeholder: str = "",
        group_files: GroupFiles = one_item_per_file,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the table.

        Args:
            file_extensions: Allowed file extensions (with leading dot) for drop/browse.
            empty_hint: Text of the empty table.
            add_more_text: Text of the button under the rows.
            describe: Text of a candidate in the menu of a row.
            query_placeholder: Hint shown in an empty query field.
            group_files: Splits added files into items.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._rows: Dict[Path, BatchRow] = {}
        # Every file in the table, with the key of its row.
        self._owner: Dict[Path, Path] = {}
        self._file_extensions = [e.lower() for e in (file_extensions or [])]
        self._add_more_btn: Optional[QPushButton] = None
        self._empty_hint = empty_hint or tr(
            "batch_drop_hint", "Drop files or folders, or click to browse"
        )
        self._add_more_text = add_more_text or tr("add_files", "+ Add files")
        self._describe = describe
        self._query_placeholder = query_placeholder
        self._group_files = group_files

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._container = Card()
        self._container.setMinimumHeight(220)
        self._container.setGraphicsEffect(card_shadow())
        self._container.setAcceptDrops(True)
        self._container.installEventFilter(self)

        scroll = StopPropagationScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")
        self._scroll = scroll

        self._inner = Card()
        self._inner.setObjectName("InnerCard")
        scroll.setWidget(self._inner)
        self._container._layout.addWidget(scroll)

        layout.addWidget(self._container)
        self.setAcceptDrops(True)
        self._show_empty(self._empty_hint)

    def set_texts(self, empty_hint: str, add_more_text: str) -> None:
        """Change the texts of the empty table and of the add button.

        Args:
            empty_hint: Text of the empty table.
            add_more_text: Text of the button under the rows.
        """
        self._empty_hint = empty_hint
        self._add_more_text = add_more_text
        if self._add_more_btn is not None:
            self._add_more_btn.setText(add_more_text)
        if not self._rows:
            self._show_empty(empty_hint)

    def _show_empty(self, text: str) -> None:
        self.clear()
        # The hint fills the card, centered.
        self._inner._layout.setAlignment(Qt.AlignmentFlag(0))
        set_empty_state(self._inner._layout, text)
        self._container.setCursor(Qt.CursorShape.PointingHandCursor)

    def clear(self) -> None:
        """Remove all rows."""
        while self._inner._layout.count() > 0:
            item = self._inner._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rows.clear()
        self._owner.clear()
        self._add_more_btn = None

    def set_files(self, files: List[Path]) -> None:
        """Populate the table with files and reset their state."""
        self.clear()
        if not files:
            self._show_empty(self._empty_hint)
            return
        for item in self._group_files(files):
            self._append_row(item)

    def add_files(self, files: List[Path]) -> List[List[Path]]:
        """Append new files to the table, ignoring those already in it.

        Returns:
            The items actually appended, each a list of files.
        """
        new = [f for f in files if f not in self._owner]
        if not new:
            return []
        if not self._rows:
            self._clear_empty_state()
        items = self._group_files(new)
        for item in items:
            self._append_row(item)
        return items

    def _append_row(self, files: List[Path]) -> None:
        # Rows keep their height at the top of the card: without this, a few
        # rows are spread over the whole height.
        self._inner._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._remove_add_more_button()
        key = files[0]
        row = BatchRow(files, self._describe, self._query_placeholder)
        row.changed.connect(self.row_changed.emit)
        row.rescan_requested.connect(
            lambda q, k=key: self.row_rescan_requested.emit(k, q)
        )
        self._rows[key] = row
        for f in files:
            self._owner[f] = key
        self._inner.add(row)
        self._container.unsetCursor()
        self._ensure_add_more_button()

    def _ensure_add_more_button(self) -> None:
        if self._add_more_btn is not None:
            return
        btn = QPushButton(self._add_more_text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(34)
        if IS_MACOS:
            btn.setObjectName("DashedButton")
            btn.setStyleSheet("QPushButton { margin: 6px; font-size: 12px; }")
        else:
            btn.setStyleSheet(
                """
            QPushButton {
                background: transparent;
                color: rgba(255, 255, 255, 0.6);
                border: 1px dashed rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                margin: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: white;
                border-color: rgba(255, 255, 255, 0.6);
                background: rgba(255, 255, 255, 0.05);
            }
            """
            )
        btn.clicked.connect(self._browse)
        self._add_more_btn = btn
        self._inner.add(btn, last=True)

    def _remove_add_more_button(self) -> None:
        if self._add_more_btn is None:
            return
        layout = self._inner._layout
        for i in range(layout.count() - 1, -1, -1):
            item = layout.itemAt(i)
            w = item.widget() if item else None
            if w is self._add_more_btn or (
                w is not None
                and w.objectName() == "Separator"
                and i == layout.count() - 2
            ):
                layout.takeAt(i)
                if w:
                    w.deleteLater()
        self._add_more_btn = None

    def _clear_empty_state(self) -> None:
        while self._inner._layout.count() > 0:
            item = self._inner._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._add_more_btn = None

    def files(self) -> List[Path]:
        """Return every file in the table."""
        return list(self._owner)

    def items(self) -> List[List[Path]]:
        """Return the files of every row, in order."""
        return [row.files for row in self._rows.values()]

    def item_files(self, key: Path) -> List[Path]:
        """Return the files of the row with this key."""
        row = self._rows.get(key)
        return row.files if row else []

    def set_row_loading(self, key: Path) -> None:
        """Mark a single row as pending."""
        row = self._rows.get(key)
        if row:
            row.set_loading()

    def fail_pending(self) -> None:
        """Show the rows still searching as Missing, after a failed search."""
        for row in self._rows.values():
            if row.get_status() == STATUS_PENDING:
                row.set_candidates([])

    def apply_search_result(self, result: BatchMatch) -> None:
        """Apply a single batch search result to its row."""
        row = self._rows.get(result.file)
        if not row:
            return
        row.set_query(result.query, result.year)
        row.set_candidates(result.candidates, result.selected, result.status)

    def apply_results(self, results: List[BatchMatch]) -> None:
        """Apply a batch of search results to their rows."""
        for r in results:
            self.apply_search_result(r)

    def update_new_names(
        self, compute: Callable[[List[Path], Dict[str, Any]], str]
    ) -> None:
        """Refresh the new-name preview for every row.

        Args:
            compute: Gives the new name from the files of a row and its
                selected candidate.
        """
        for row in self._rows.values():
            cand = row.get_selected_candidate()
            row.set_new_name(compute(row.files, cand) if cand else "")

    def get_mappings(self) -> List[tuple]:
        """Return [(files, selected_candidate_dict_or_None), ...] for every row."""
        return [(r.files, r.get_selected_candidate()) for r in self._rows.values()]

    def get_ready_mappings(self) -> List[tuple]:
        """Return [(files, candidate), ...] for the rows that are Ready.

        A row to pick is left out even if a candidate is selected: the user
        has not confirmed it.
        """
        return [
            (r.files, r.get_selected_candidate())
            for r in self._rows.values()
            if r.get_status() == STATUS_OK and r.get_selected_candidate()
        ]

    def remove_files(self, files: List[Path]) -> None:
        """Remove the rows that hold any of the given files, such as renamed ones."""
        layout = self._inner._layout
        keys = list(dict.fromkeys(self._owner[f] for f in files if f in self._owner))
        for key in keys:
            row = self._rows.pop(key)
            for f in row.files:
                self._owner.pop(f, None)
            idx = layout.indexOf(row)
            if idx < 0:
                row.deleteLater()
                continue
            # Card.add() puts a separator before every row but the first.
            sep_idx = idx - 1 if idx > 0 else idx + 1
            sep = layout.itemAt(sep_idx).widget() if layout.itemAt(sep_idx) else None
            layout.removeWidget(row)
            row.deleteLater()
            if sep is not None and sep.objectName() == "Separator":
                layout.removeWidget(sep)
                sep.deleteLater()
        if not self._rows:
            self.set_files([])

    def count_by_status(self) -> Dict[str, int]:
        """Return a count of rows per status."""
        counts: Dict[str, int] = {
            STATUS_OK: 0,
            STATUS_AMBIGUOUS: 0,
            STATUS_MISSING: 0,
            STATUS_PENDING: 0,
        }
        for r in self._rows.values():
            counts[r.get_status()] = counts.get(r.get_status(), 0) + 1
        return counts

    def has_rows(self) -> bool:
        """Return True if at least one row is loaded."""
        return bool(self._rows)

    # ----------------------------------------------------- drag/drop & click

    def _filter_supported(self, paths: List[Path]) -> List[Path]:
        """Return the supported files, looking inside dropped folders."""
        files: List[Path] = []
        for p in paths:
            if p.is_dir():
                files.extend(sorted(f for f in p.rglob("*") if f.is_file()))
            elif p.is_file():
                files.append(p)
        if not self._file_extensions:
            return files
        return [f for f in files if f.suffix.lower() in self._file_extensions]

    def _browse(self) -> None:
        filter_str = ""
        if self._file_extensions:
            exts = " ".join(f"*{e}" for e in self._file_extensions)
            filter_str = f"{tr('files', 'Files')} ({exts})"
        files, _ = QFileDialog.getOpenFileNames(
            self, tr("select_files_dialog", "Select files"), "", filter_str
        )
        if not files:
            return
        paths = self._filter_supported([Path(f) for f in files])
        appended = self.add_files(paths)
        if appended:
            self.files_added.emit(appended)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent

        if obj is self._container:
            etype = event.type()
            if etype == QEvent.Type.DragEnter:
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                    return True
            elif etype == QEvent.Type.Drop:
                urls = event.mimeData().urls()
                paths = self._filter_supported([Path(u.toLocalFile()) for u in urls])
                if paths:
                    appended = self.add_files(paths)
                    if appended:
                        self.files_added.emit(appended)
                event.acceptProposedAction()
                return True
            elif etype == QEvent.Type.MouseButtonRelease and not self._rows:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._browse()
                    return True
        return super().eventFilter(obj, event)
