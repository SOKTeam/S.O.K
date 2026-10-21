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
"""Rename history: what each rename did, and how to undo it.

A rename runs inside record(): the file operations report each move
(move_file), each folder they create (make_folders) and each poster they
save to the active Journal. At the end, the journal becomes an Operation of
the HistoryStore, saved in history.json next to the settings.

Undoing puts the files back where they were, but never replaces a file: a
file moved or deleted since, or an old place taken by another file, is
skipped. The .backup kept for a replaced file is put back, the posters the
rename saved are deleted once all their files are back, and the folders it
created are removed when they are empty.
"""

import json
import logging
import os
import shutil
import threading
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

# Operations kept; older ones are dropped.
MAX_OPERATIONS = 100

# Why a file was not put back (UndoReport.skipped).
MISSING = "missing"
OCCUPIED = "occupied"
FAILED = "failed"


@dataclass
class Move:
    """One file of a rename: where it was, where it went."""

    source: str
    target: str
    # The file it replaced, kept as "<target>.backup".
    backup: Optional[str] = None
    undone: bool = False


@dataclass
class Artwork:
    """A poster or cover saved by a rename, and the files it belongs to."""

    path: str
    files: List[str]
    removed: bool = False


@dataclass
class Operation:
    """One rename: all the files of one click on "Rename all"."""

    id: str
    date: str
    kind: str
    moves: List[Move] = field(default_factory=list)
    folders: List[str] = field(default_factory=list)
    artwork: List[Artwork] = field(default_factory=list)

    @property
    def undone(self) -> bool:
        """True when every file was put back."""
        return all(move.undone for move in self.moves)

    @property
    def partly_undone(self) -> bool:
        """True when some files, but not all, were put back."""
        return any(move.undone for move in self.moves) and not self.undone

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Operation":
        return cls(
            id=data["id"],
            date=data["date"],
            kind=data.get("kind", ""),
            moves=[Move(**move) for move in data.get("moves", [])],
            folders=list(data.get("folders", [])),
            artwork=[Artwork(**art) for art in data.get("artwork", [])],
        )


@dataclass
class UndoReport:
    """What an undo did: the files put back and the files left in place."""

    restored: List[Move] = field(default_factory=list)
    # (move, MISSING / OCCUPIED / FAILED)
    skipped: List[tuple] = field(default_factory=list)


class Journal:
    """What a rename does, reported by the file operations as it goes."""

    def __init__(self) -> None:
        self.moves: List[Move] = []
        self.folders: List[str] = []
        self.artwork: List[Artwork] = []
        # Id of the Operation saved at the end of record(), if any.
        self.operation_id: Optional[str] = None

    def moved(self, source: str, target: str, backup: Optional[str]) -> None:
        self.moves.append(Move(str(source), str(target), backup))

    def created_folders(self, folders: List[str]) -> None:
        self.folders.extend(str(folder) for folder in folders)

    def saved_artwork(self, path: str, files: List[str]) -> None:
        self.artwork.append(Artwork(str(path), [str(f) for f in files]))


def content_kind(media_item: Any) -> str:
    """The kind of an operation: the ContentType value of its item."""
    content_type = getattr(media_item, "content_type", None)
    return getattr(content_type, "value", "") or ""


_journal: ContextVar[Optional[Journal]] = ContextVar("rename_journal", default=None)


def current_journal() -> Optional[Journal]:
    """The journal of the rename running in this thread, if any."""
    return _journal.get()


@contextmanager
def record(kind: str, store: Optional["HistoryStore"] = None) -> Iterator[Journal]:
    """Record the rename run in the block as one operation of the history.

    Args:
        kind: What was renamed, a ContentType value such as "movie".
        store: The history to add it to (get_history() by default).

    Yields:
        The journal; its operation_id is set at the end when files moved.
    """
    journal = Journal()
    token = _journal.set(journal)
    try:
        yield journal
    finally:
        _journal.reset(token)
        if journal.moves:
            operation = Operation(
                id=uuid.uuid4().hex,
                date=datetime.now().isoformat(timespec="seconds"),
                kind=kind,
                moves=journal.moves,
                folders=journal.folders,
                artwork=journal.artwork,
            )
            (store or get_history()).add(operation)
            journal.operation_id = operation.id


class HistoryStore:
    """The operations of the history, newest first, saved in a JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._operations: List[Operation] = self._load()

    def _load(self) -> List[Operation]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [Operation.from_dict(op) for op in data.get("operations", [])]
        except FileNotFoundError:
            return []
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Unreadable rename history %s: %s", self.path, exc)
            return []

    def _save(self) -> None:
        data = {"operations": [asdict(op) for op in self._operations]}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            partial = self.path.with_name(self.path.name + ".part")
            partial.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            os.replace(partial, self.path)
        except OSError as exc:
            logger.warning("Could not save the rename history: %s", exc)

    def operations(self) -> List[Operation]:
        """The operations, newest first."""
        with self._lock:
            return list(self._operations)

    def get(self, operation_id: str) -> Optional[Operation]:
        with self._lock:
            return next((op for op in self._operations if op.id == operation_id), None)

    def add(self, operation: Operation) -> None:
        """Add an operation, dropping the oldest beyond MAX_OPERATIONS."""
        with self._lock:
            self._operations.insert(0, operation)
            del self._operations[MAX_OPERATIONS:]
            self._save()

    def clear(self) -> None:
        with self._lock:
            self._operations = []
            self._save()

    def undo(self, operation_id: str, index: Optional[int] = None) -> UndoReport:
        """Put the files of an operation back where they were.

        Args:
            operation_id: The operation.
            index: One file of it (its position in moves), or None for all.

        Returns:
            The files put back and the ones left in place, with why.
        """
        report = UndoReport()
        with self._lock:
            operation = self.get(operation_id)
            if operation is None:
                return report
            moves = operation.moves if index is None else [operation.moves[index]]
            # Last moved, first put back: a later file may have taken the
            # place of an earlier one.
            for move in reversed(moves):
                if move.undone:
                    continue
                reason = _put_back(move)
                if reason:
                    report.skipped.append((move, reason))
                else:
                    move.undone = True
                    report.restored.append(move)
            _remove_artwork(operation)
            _remove_folders(operation)
            self._save()
        return report


def _put_back(move: Move) -> Optional[str]:
    """Move a file back to its source; return why it could not be, if so."""
    if not os.path.exists(move.target):
        return MISSING
    if os.path.exists(move.source):
        return OCCUPIED
    try:
        os.makedirs(os.path.dirname(move.source) or ".", exist_ok=True)
        try:
            os.replace(move.target, move.source)
        except OSError:
            shutil.move(move.target, move.source)
        if move.backup and os.path.exists(move.backup):
            os.replace(move.backup, move.target)
    except OSError as exc:
        logger.warning("Undo failed for %s: %s", move.target, exc)
        return FAILED
    return None


def _remove_artwork(operation: Operation) -> None:
    """Delete the posters saved by the operation whose files are all back."""
    undone = {move.target for move in operation.moves if move.undone}
    for art in operation.artwork:
        if art.removed or not all(f in undone for f in art.files):
            continue
        try:
            os.remove(art.path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.warning("Could not delete %s: %s", art.path, exc)
            continue
        art.removed = True


# Files the system adds to a folder that was opened: a folder holding only
# these is empty.
SYSTEM_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}


def _remove_folders(operation: Operation) -> None:
    """Remove the folders the operation created, deepest first, if empty."""
    for folder in sorted(set(operation.folders), key=len, reverse=True):
        try:
            names = os.listdir(folder)
            if any(name not in SYSTEM_FILES for name in names):
                continue
            for name in names:
                os.remove(os.path.join(folder, name))
            os.rmdir(folder)
        except OSError:
            # Already gone, or not allowed: leave it.
            pass


_history: Optional[HistoryStore] = None
_history_lock = threading.Lock()


def get_history() -> HistoryStore:
    """The history of the application, in history.json next to the settings."""
    global _history
    with _history_lock:
        if _history is None:
            from sok.config.config_manager import get_config_manager

            folder = get_config_manager().config_path.parent
            _history = HistoryStore(folder / "history.json")
        return _history
