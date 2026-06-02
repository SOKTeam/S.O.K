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
"""Table-style widget for batch movie renaming.

Each row represents one source file and lets the user pick a TMDB match
among candidates, edit the search query, and preview the new name.
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

from sok.ui.components.base import Card
from sok.ui.components.window import StopPropagationScrollArea
from sok.ui.controllers.ui_state import set_empty_state
from sok.ui.i18n import tr
from sok.ui.theme import Theme, card_shadow

logger = logging.getLogger(__name__)


STATUS_OK = "ok"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_MISSING = "missing"
STATUS_PENDING = "pending"


class MovieRow(QWidget):
    """Single row in the movie batch table.

    Signals:
        changed: Emitted when the user changes the selected candidate or query.
        rescan_requested: Emitted when the user clicks the rescan button.
    """

    changed = Signal()
    rescan_requested = Signal(str)

    def __init__(self, file: Path, parent: Optional[QWidget] = None):
        """Initialize a movie row.

        Args:
            file: Source file path.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._file = file
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
        self._original_lbl = QLabel(file.name)
        self._original_lbl.setStyleSheet(
            f"color: {Theme.DARK['secondary']}; font-size: 11px;"
        )
        self._original_lbl.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self._new_name_lbl = QLabel("...")
        self._new_name_lbl.setStyleSheet(
            f"color: {Theme.DARK['tertiary']}; font-size: 12px; font-style: italic;"
        )
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
            tr("movie_title_year", "Title (optional year)")
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
        self._match_combo.currentIndexChanged.connect(self._on_match_changed)
        mid.addWidget(self._match_combo)
        layout.addLayout(mid, 3)

        self._status_lbl = QLabel("…")
        self._status_lbl.setFixedWidth(80)
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setStyleSheet(
            f"color: {Theme.DARK['secondary']}; font-size: 11px; font-weight: 600;"
        )
        layout.addWidget(self._status_lbl)

    @property
    def file(self) -> Path:
        """Return the source file path."""
        return self._file

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

    def set_candidates(self, candidates: List[Dict[str, Any]]) -> None:
        """Populate the candidates combobox.

        Args:
            candidates: List of TMDB result dicts.
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
                title = (
                    cand.get("title") or cand.get("name") or tr("unknown", "Unknown")
                )
                year = (cand.get("release_date") or "")[:4]
                label = f"{title} ({year})" if year else title
                self._match_combo.addItem(label, cand)
            self._match_combo.setCurrentIndex(0)
            self.set_status(STATUS_OK if len(candidates) == 1 else STATUS_AMBIGUOUS)
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
            self._new_name_lbl.setStyleSheet(
                f"color: {Theme.DARK['green']}; font-size: 12px; font-weight: 600;"
            )
        else:
            self._new_name_lbl.setText("...")
            self._new_name_lbl.setStyleSheet(
                f"color: {Theme.DARK['tertiary']}; font-size: 12px; font-style: italic;"
            )

    def set_status(self, status: str) -> None:
        """Set the visual status badge."""
        self._status = status
        if status == STATUS_OK:
            text, color = "✓ " + tr("status_ready", "Ready"), Theme.DARK["green"]
        elif status == STATUS_AMBIGUOUS:
            text, color = "⚠ " + tr("status_ambiguous", "Pick one"), "#FFB347"
        elif status == STATUS_MISSING:
            text, color = "✗ " + tr("status_missing", "Missing"), Theme.DARK["red"]
        else:
            text, color = "…", Theme.DARK["secondary"]
        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 600;"
        )

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


class MovieBatchTable(QWidget):
    """Scrollable table of MovieRow widgets.

    Signals:
        row_changed: Emitted when any row's selection or query changes.
        row_rescan_requested(Path, str): Emitted when a row requests a re-scan.
    """

    row_changed = Signal()
    row_rescan_requested = Signal(object, str)
    files_added = Signal(list)

    def __init__(
        self,
        file_extensions: Optional[List[str]] = None,
        parent: Optional[QWidget] = None,
    ):
        """Initialize the table.

        Args:
            file_extensions: Allowed file extensions (with leading dot) for drop/browse.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._rows: Dict[Path, MovieRow] = {}
        self._file_extensions = [e.lower() for e in (file_extensions or [])]
        self._add_more_btn: Optional[QPushButton] = None

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
        self._show_empty(tr("movies_drop_hint", "Drop video files or click to browse"))

    def _show_empty(self, text: str) -> None:
        self.clear()
        set_empty_state(self._inner._layout, text)
        self._container.setCursor(Qt.CursorShape.PointingHandCursor)

    def clear(self) -> None:
        """Remove all rows."""
        while self._inner._layout.count() > 0:
            item = self._inner._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rows.clear()
        self._add_more_btn = None

    def set_files(self, files: List[Path]) -> None:
        """Populate the table with files and reset their state."""
        self.clear()
        if not files:
            self._show_empty(
                tr("movies_drop_hint", "Drop video files or click to browse")
            )
            return
        for f in files:
            self._append_row(f)

    def add_files(self, files: List[Path]) -> List[Path]:
        """Append new files to the table, ignoring duplicates.

        Returns the actually appended paths.
        """
        if not files:
            return []
        if not self._rows:
            self._clear_empty_state()
        appended: List[Path] = []
        for f in files:
            if f in self._rows:
                continue
            self._append_row(f)
            appended.append(f)
        return appended

    def _append_row(self, file: Path) -> None:
        self._remove_add_more_button()
        row = MovieRow(file)
        row.changed.connect(self.row_changed.emit)
        row.rescan_requested.connect(
            lambda q, p=file: self.row_rescan_requested.emit(p, q)
        )
        self._rows[file] = row
        self._inner.add(row)
        self._container.unsetCursor()
        self._ensure_add_more_button()

    def _ensure_add_more_button(self) -> None:
        if self._add_more_btn is not None:
            return
        btn = QPushButton(tr("add_more_movies", "+ Add more movies"))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(34)
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
        """Return the list of files currently in the table."""
        return list(self._rows.keys())

    def set_row_loading(self, file: Path) -> None:
        """Mark a single row as pending."""
        row = self._rows.get(file)
        if row:
            row.set_loading()

    def apply_search_result(self, result: Dict[str, Any]) -> None:
        """Apply a single batch search result to its row."""
        file = result.get("file")
        row = self._rows.get(file) if file else None
        if not row:
            return
        row.set_query(result.get("query", ""), result.get("year"))
        row.set_candidates(result.get("candidates", []))

    def apply_results(self, results: List[Dict[str, Any]]) -> None:
        """Apply a batch of search results to their rows."""
        for r in results:
            self.apply_search_result(r)

    def update_new_names(self, compute: Callable[[Path, Dict[str, Any]], str]) -> None:
        """Refresh the new-name preview for every row."""
        for file, row in self._rows.items():
            cand = row.get_selected_candidate()
            new_name = compute(file, cand) if cand else ""
            row.set_new_name(new_name)

    def get_mappings(self) -> List[tuple]:
        """Return [(file, selected_candidate_dict_or_None), ...] for every row."""
        return [(f, r.get_selected_candidate()) for f, r in self._rows.items()]

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
        if not self._file_extensions:
            return [p for p in paths if p.is_file()]
        return [
            p
            for p in paths
            if p.is_file() and p.suffix.lower() in self._file_extensions
        ]

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
