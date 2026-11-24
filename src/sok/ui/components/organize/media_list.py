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
"""List of a batch page: one FileRow per item, and the item selected.

Same interface as the table it replaced, so the pages keep their logic:
files are added, searched, given a candidate, renamed and removed by key
(the first file of the item). The query and the choice of a candidate are
no longer edited in the row but on the scene of the page (see BatchPage).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from sok.core.batch import (
    STATUS_AMBIGUOUS,
    STATUS_MISSING,
    STATUS_READY,
    BatchMatch,
    candidate_year,
)
from sok.ui.components.file_row import CoverTile, FileRow, RowData
from sok.ui.i18n import tr

STATUS_OK = STATUS_READY
STATUS_PENDING = "pending"

# Text of a candidate in the pick list.
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


# Turns an entry into what its row shows.
MakeRow = Callable[["Entry"], RowData]
# What the selected row shows under it (the episodes of a series), or None.
MakeDetail = Callable[["Entry"], Optional[QWidget]]


@dataclass
class Entry:
    """An item of the list and its search.

    Attributes:
        files: Source files; the first one names the item and is its key.
        query: Search text, read from the file name or typed by the user.
        year: Year read from the file name, or None.
        candidates: Search results.
        selected: Index of the chosen candidate, or None.
        status: STATUS_READY, STATUS_AMBIGUOUS, STATUS_MISSING or pending.
        new_name: New name of the first file, or "".
    """

    files: List[Path]
    query: str = ""
    year: Optional[int] = None
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    selected: Optional[int] = None
    status: str = STATUS_PENDING
    new_name: str = ""

    @property
    def key(self) -> Path:
        return self.files[0]

    @property
    def candidate(self) -> Optional[Dict[str, Any]]:
        """The chosen candidate, if any."""
        if self.selected is None or not self.candidates:
            return None
        return self.candidates[self.selected]

    @property
    def confidence(self) -> int:
        """Filled notches of the gauge, from the status.

        5: Ready, and the name gave the year too; 4: Ready from the title
        only; 2: several results possible; 0: nothing found yet.
        """
        if self.status == STATUS_READY:
            return 5 if self.year else 4
        if self.status == STATUS_AMBIGUOUS:
            return 2
        return 0


class _TileGrid(QWidget):
    """Places CoverTiles in columns of equal width, rows of equal height."""

    COLUMNS = 4
    GAP_X, GAP_Y = 22, 28

    def __init__(self) -> None:
        super().__init__()
        self._tiles: List[CoverTile] = []
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def add(self, tile: CoverTile) -> None:
        tile.setParent(self)
        tile.show()
        self._tiles.append(tile)
        self._place()

    def remove(self, tile: CoverTile) -> None:
        if tile in self._tiles:
            self._tiles.remove(tile)
        self._place()

    def resizeEvent(self, e):  # noqa: N802 - Qt API
        super().resizeEvent(e)
        self._place()

    def _place(self) -> None:
        width = max(1, self.width() - 14)
        column = (width - (self.COLUMNS - 1) * self.GAP_X) / self.COLUMNS
        height = 0
        for index, tile in enumerate(self._tiles):
            row, col = divmod(index, self.COLUMNS)
            tile_height = tile.height_for(int(column))
            x = round(col * (column + self.GAP_X))
            y = row * (tile_height + self.GAP_Y)
            tile.setGeometry(x, y, int(column), tile_height)
            height = y + tile_height
        self.setMinimumHeight(height)


class MediaList(QWidget):
    """Scrollable list of FileRows, one per item, with a selected item.

    Signals:
        row_changed: The candidate or the status of an item changed.
        row_rescan_requested(Path, str): An item asks for a new search, with
            its key and the query.
        files_added(list): Items added by a drop, each a list of files.
        current_changed(object): Key of the selected item, or None.
    """

    row_changed = Signal()
    row_rescan_requested = Signal(object, str)
    files_added = Signal(list)
    current_changed = Signal(object)

    def __init__(
        self,
        make_row: MakeRow,
        file_extensions: Optional[List[str]] = None,
        describe: Describe = describe_dated,
        group_files: GroupFiles = one_item_per_file,
        make_detail: Optional[MakeDetail] = None,
        grid: bool = False,
        parent: Optional[QWidget] = None,
    ):
        """Build an empty list.

        Args:
            make_row: Gives the RowData of an entry.
            file_extensions: Accepted extensions (with the dot) for drops.
            describe: Text of a candidate, for the pick list of the scene.
            group_files: Splits added files into items.
            make_detail: What the selected row shows under it, if anything.
            grid: Show the items as cover tiles in a grid (albums).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._make_row = make_row
        self._file_extensions = [e.lower() for e in (file_extensions or [])]
        self.describe = describe
        self._group_files = group_files
        self._entries: Dict[Path, Entry] = {}
        self._rows: Dict[Path, Any] = {}
        # Every file of the list, with the key of its item.
        self._owner: Dict[Path, Path] = {}
        self._current: Optional[Path] = None
        self._was_label = "was"
        self._make_detail = make_detail
        self._detail: Optional[QWidget] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Only the viewport: a stylesheet on the scroll area would draw its
        # scroll bar with Qt instead of the system (arrows on macOS).
        self._scroll.viewport().setStyleSheet("background: transparent;")
        self._grid: Optional[_TileGrid] = _TileGrid() if grid else None
        inner = QWidget()
        inner.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._rows_layout = QVBoxLayout(inner)
        # Room at the right for the scroll bar, over no row.
        self._rows_layout.setContentsMargins(0, 0, 14, 0)
        self._rows_layout.setSpacing(2)
        self._rows_layout.addStretch()
        self._scroll.setWidget(self._grid if self._grid is not None else inner)
        layout.addWidget(self._scroll)
        self.setAcceptDrops(True)

    # ------------------------------------------------------------- Texts

    def set_was_label(self, text: str) -> None:
        """Set the translated word written before the original name."""
        self._was_label = text
        for row in self._rows.values():
            row.set_was_label(text)

    def set_texts(self, *_args) -> None:
        """Kept for the pages: the empty state is now a screen of the page."""

    # ------------------------------------------------------------- Items

    def clear(self) -> None:
        """Remove every item."""
        for row in self._rows.values():
            row.deleteLater()
        if self._detail is not None:
            self._detail.deleteLater()
            self._detail = None
        self._entries.clear()
        self._rows.clear()
        self._owner.clear()
        self._set_current(None)

    def set_files(self, files: List[Path]) -> None:
        """Replace the items with these files."""
        self.clear()
        self.add_files(files)

    def add_files(self, files: List[Path]) -> List[List[Path]]:
        """Append new files, ignoring those already in the list.

        Returns:
            The items actually appended, each a list of files.
        """
        new = [f for f in files if f not in self._owner]
        if not new:
            return []
        items = self._group_files(new)
        for item in items:
            self._append(item)
        if self._current is None and items:
            self._set_current(items[0][0])
        return items

    def _append(self, files: List[Path]) -> None:
        entry = Entry(list(files), query=files[0].stem)
        key = entry.key
        self._entries[key] = entry
        for f in files:
            self._owner[f] = key
        data = self._make_row(entry)
        row: CoverTile | FileRow
        if self._grid is not None:
            tile = CoverTile(data, self._was_label)
            self._grid.add(tile)
            row = tile
        else:
            row = FileRow(data, self._was_label)
            self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)
        row.clicked.connect(lambda k=key: self._set_current(k))
        self._rows[key] = row

    def files(self) -> List[Path]:
        """Return every file of the list."""
        return list(self._owner)

    def items(self) -> List[List[Path]]:
        """Return the files of every item, in order."""
        return [list(e.files) for e in self._entries.values()]

    def item_files(self, key: Path) -> List[Path]:
        entry = self._entries.get(key)
        return list(entry.files) if entry else []

    def entry(self, key: Optional[Path]) -> Optional[Entry]:
        """Return the entry of a key, or None."""
        return self._entries.get(key) if key is not None else None

    def entries(self) -> List[Entry]:
        return list(self._entries.values())

    def has_rows(self) -> bool:
        return bool(self._entries)

    def refresh_row(self, key: Path) -> None:
        """Draw a row again from its entry, and its detail if selected."""
        row = self._rows.get(key)
        entry = self._entries.get(key)
        if row and entry:
            row.set_data(self._make_row(entry))
            if key == self._current:
                self._show_detail()

    def _show_detail(self) -> None:
        """Put the detail of the selected row under it."""
        if self._detail is not None:
            self._rows_layout.removeWidget(self._detail)
            self._detail.deleteLater()
            self._detail = None
        entry = self._entries.get(self._current) if self._current else None
        if entry is None or self._make_detail is None or self._grid is not None:
            return
        detail = self._make_detail(entry)
        if detail is None:
            return
        index = self._rows_layout.indexOf(self._rows[entry.key])
        self._rows_layout.insertWidget(index + 1, detail)
        self._detail = detail

    def refresh_rows(self) -> None:
        for key in self._entries:
            self.refresh_row(key)

    # ------------------------------------------------------------ Selection

    def current(self) -> Optional[Path]:
        """Key of the selected item, or None."""
        return self._current

    def _set_current(self, key: Optional[Path]) -> None:
        if key is not None and key not in self._entries:
            key = None
        self._current = key
        for k, row in self._rows.items():
            row.set_selected(k == key)
        self._show_detail()
        if key is not None and key in self._rows:
            self._scroll.ensureWidgetVisible(self._rows[key])
        self.current_changed.emit(key)

    def set_current(self, key: Optional[Path]) -> None:
        self._set_current(key)

    def select_next(self, step: int = 1) -> None:
        """Select the next (or, with -1, the previous) item."""
        keys = list(self._entries)
        if not keys:
            return
        index = keys.index(self._current) if self._current in keys else -1
        self._set_current(keys[max(0, min(len(keys) - 1, index + step))])

    # --------------------------------------------------------------- Search

    def set_row_loading(self, key: Path) -> None:
        entry = self._entries.get(key)
        if entry:
            entry.candidates, entry.selected = [], None
            entry.status, entry.new_name = STATUS_PENDING, ""
            self.refresh_row(key)

    def fail_pending(self) -> None:
        """Show the items still searching as not found, after a failed search."""
        for entry in self._entries.values():
            if entry.status == STATUS_PENDING:
                entry.status = STATUS_MISSING
                self.refresh_row(entry.key)

    def apply_search_result(self, result: BatchMatch) -> None:
        entry = self._entries.get(result.file)
        if not entry:
            return
        entry.query = (result.query or "").strip()
        entry.year = result.year
        entry.candidates = list(result.candidates)
        if not entry.candidates:
            entry.selected, entry.status = None, STATUS_MISSING
        else:
            entry.selected = result.selected or 0
            entry.status = result.status
        self.refresh_row(entry.key)
        self.row_changed.emit()
        if entry.key == self._current:
            self.current_changed.emit(entry.key)

    def apply_results(self, results: List[BatchMatch]) -> None:
        for result in results:
            self.apply_search_result(result)

    def choose(self, key: Path, index: int) -> None:
        """Confirm a candidate of an item: the item becomes Ready."""
        entry = self._entries.get(key)
        if not entry or not 0 <= index < len(entry.candidates):
            return
        entry.selected, entry.status = index, STATUS_OK
        self.refresh_row(key)
        self.row_changed.emit()
        if key == self._current:
            self.current_changed.emit(key)

    def request_search(self, key: Path, query: str) -> None:
        """Ask the page for a new search of an item."""
        query = query.strip()
        if key in self._entries and query:
            self.row_rescan_requested.emit(key, query)

    def update_new_names(
        self, compute: Callable[[List[Path], Dict[str, Any]], str]
    ) -> None:
        for entry in self._entries.values():
            candidate = entry.candidate
            entry.new_name = compute(entry.files, candidate) if candidate else ""
            self.refresh_row(entry.key)

    def get_mappings(self) -> List[tuple]:
        return [(list(e.files), e.candidate) for e in self._entries.values()]

    def get_ready_mappings(self) -> List[tuple]:
        """[(files, candidate)] of the Ready items."""
        return [
            (list(e.files), e.candidate)
            for e in self._entries.values()
            if e.status == STATUS_OK and e.candidate
        ]

    def remove_files(self, files: List[Path]) -> None:
        """Remove the items that hold any of these files."""
        keys = list(dict.fromkeys(self._owner[f] for f in files if f in self._owner))
        order = list(self._entries)
        for key in keys:
            entry = self._entries.pop(key)
            for f in entry.files:
                self._owner.pop(f, None)
            row = self._rows.pop(key)
            if self._grid is not None:
                self._grid.remove(row)
            else:
                self._rows_layout.removeWidget(row)
            row.deleteLater()
        if self._current in keys:
            rest = [k for k in order if k in self._entries]
            following = [k for k in rest if order.index(k) > order.index(self._current)]
            nxt: List[Optional[Path]] = [*following, *rest, None]
            self._set_current(nxt[0])

    def count_by_status(self) -> Dict[str, int]:
        counts: Dict[str, int] = {
            STATUS_OK: 0,
            STATUS_AMBIGUOUS: 0,
            STATUS_MISSING: 0,
            STATUS_PENDING: 0,
        }
        for entry in self._entries.values():
            counts[entry.status] = counts.get(entry.status, 0) + 1
        return counts

    # ---------------------------------------------------------------- Drops

    def filter_supported(self, paths: List[Path]) -> List[Path]:
        """Return the supported files, looking inside folders."""
        files: List[Path] = []
        for p in paths:
            if p.is_dir():
                files.extend(sorted(f for f in p.rglob("*") if f.is_file()))
            elif p.is_file():
                files.append(p)
        if not self._file_extensions:
            return files
        return [f for f in files if f.suffix.lower() in self._file_extensions]

    def add_paths(self, paths: List[Path]) -> None:
        """Add dropped or chosen files and folders, and announce them."""
        appended = self.add_files(self.filter_supported(paths))
        if appended:
            self.files_added.emit(appended)

    def dragEnterEvent(self, event):  # noqa: N802 - Qt API
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802 - Qt API
        self.add_paths([Path(u.toLocalFile()) for u in event.mimeData().urls()])
        event.acceptProposedAction()
