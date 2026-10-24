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
"""The rename history of S.O.K Server, in the database, and the files
already processed.

The history of the desktop app (sok.core.history) records the renames and
undoes them; only where it keeps them changes: the history table of sok.db
instead of history.json. Each operation is one row, newest first
(position 0), with the media type of its tab.

An operation made by the automatic sorting is told apart by its rename: the
renames table keeps whether it was automatic, and the result names the
operation.

A file renamed is also "processed": with a hard link or a copy it stays in
the downloads, and the next analyses leave it out while it keeps its path,
size and date. The processed table is not limited to the 100 operations of
the history. It is written in the same transaction as the history: a
rename adds its files, an undo removes them.
"""

import json
import os
import sqlite3
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Set

from sok.core.history import MAX_OPERATIONS, HistoryStore, Operation, UndoReport
from sok.server.db import Database

# The media type (tab) of the kind of an operation, a ContentType value.
MEDIA_TYPE_OF_KIND = {
    "movie": "movies",
    "tv_series": "tv",
    "episode": "tv",
    "album": "music",
    "track": "music",
    "book": "books",
    "game": "games",
}


class UnknownOperation(LookupError):
    """No operation of the history has this id, or no file this index."""


class History(HistoryStore):
    """The operations of the history, newest first, saved in the database."""

    def __init__(self, db: Database) -> None:
        self._db = db
        super().__init__(db.path)

    def _load(self) -> List[Operation]:
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT operation FROM history ORDER BY position"
            ).fetchall()
        return [Operation.from_dict(json.loads(row["operation"])) for row in rows]

    def _save(self) -> None:
        with self._db.transaction() as conn:
            self._write(conn)

    def _write(self, conn: sqlite3.Connection) -> None:
        """Save the operations; the files undone are no longer processed."""
        conn.execute("DELETE FROM history")
        conn.executemany(
            "INSERT INTO history (id, position, date, kind, media_type, operation)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    op.id,
                    position,
                    op.date,
                    op.kind,
                    MEDIA_TYPE_OF_KIND.get(op.kind, ""),
                    json.dumps(asdict(op), ensure_ascii=False),
                )
                for position, op in enumerate(self._operations)
            ],
        )
        conn.executemany(
            "DELETE FROM processed WHERE path = ? AND operation_id = ?",
            [
                (move.source, op.id)
                for op in self._operations
                for move in op.moves
                if move.undone
            ],
        )

    def add(self, operation: Operation) -> None:
        """Add an operation, and its files still at their old place (linked or
        copied) to the files processed."""
        with self._lock:
            self._operations.insert(0, operation)
            del self._operations[MAX_OPERATIONS:]
            with self._db.transaction() as conn:
                self._write(conn)
                conn.executemany(
                    "INSERT OR REPLACE INTO processed"
                    " (path, size, mtime_ns, target, operation_id, date)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    _processed(operation),
                )

    def automatic(self) -> Set[str]:
        """The ids of the operations made by the automatic sorting."""
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT result FROM renames WHERE auto = 1 AND result IS NOT NULL"
            ).fetchall()
        return {
            operation
            for row in rows
            if (operation := json.loads(row["result"]).get("operation"))
        }

    def undo_checked(self, operation_id: str, index: Any = None) -> UndoReport:
        """undo(), for an operation and a file that exist.

        Raises:
            UnknownOperation: No operation has this id, or no file this index.
        """
        operation = self.get(operation_id)
        if operation is None:
            raise UnknownOperation(operation_id)
        if index is not None and not 0 <= index < len(operation.moves):
            raise UnknownOperation(index)
        return self.undo(operation_id, index)


def _processed(operation: Operation) -> Iterable[tuple]:
    """The rows of the processed table for the files of an operation.

    The subtitles are left out: the analyses never list them.
    """
    for move in operation.moves:
        if move.follows:
            continue
        try:
            stat = os.stat(move.source)
        except OSError:
            # Moved: nothing left to hide.
            continue
        yield (
            move.source,
            stat.st_size,
            stat.st_mtime_ns,
            move.target,
            operation.id,
            operation.date,
        )


def describe(operation: Operation, auto: bool = False) -> Dict[str, Any]:
    """An operation as the History page shows it.

    Args:
        operation: The operation.
        auto: Made by the automatic sorting.
    """
    return {
        "id": operation.id,
        "date": operation.date,
        "kind": operation.kind,
        "media_type": MEDIA_TYPE_OF_KIND.get(operation.kind, ""),
        "auto": auto,
        "undone": operation.undone,
        "partly_undone": operation.partly_undone,
        "files": [
            {
                "index": index,
                "source": move.source,
                "target": move.target,
                "mode": move.mode,
                "undone": move.undone,
                # The new path of the video a subtitle goes with.
                "follows": move.follows,
            }
            for index, move in enumerate(operation.moves)
        ],
    }


def undo_report(report: UndoReport) -> Dict[str, Any]:
    """What an undo did, for the answer of the request."""
    return {
        "restored": [move.source for move in report.restored],
        "skipped": [
            {"source": move.source, "target": move.target, "reason": reason}
            for move, reason in report.skipped
        ],
    }


def processed_files(db: Database) -> List[Dict[str, Any]]:
    """The files processed, newest first: the filter "already processed"."""
    with db.transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM processed ORDER BY date DESC, path"
        ).fetchall()
    return [
        {
            "path": row["path"],
            "target": row["target"],
            "size": row["size"],
            "date": row["date"],
            "operation": row["operation_id"],
        }
        for row in rows
    ]


def forget_processed(db: Database, paths: List[str]) -> int:
    """Analyze these files again: they are no longer processed.

    Returns:
        How many were processed.
    """
    with db.transaction() as conn:
        return conn.executemany(
            "DELETE FROM processed WHERE path = ?", [(p,) for p in paths]
        ).rowcount


def unchanged(path: str, size: int, mtime_ns: int) -> bool:
    """Whether a file still has the size and the date it was processed with."""
    try:
        stat = os.stat(path)
    except OSError:
        return False
    return stat.st_size == size and stat.st_mtime_ns == mtime_ns
