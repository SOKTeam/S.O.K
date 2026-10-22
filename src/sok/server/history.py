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
"""The rename history of S.O.K Server, in the database.

The history of the desktop app (sok.core.history) records the renames and
undoes them; only where it keeps them changes: the history table of sok.db
instead of history.json. Each operation is one row, newest first
(position 0), with the media type of its tab.
"""

import json
from dataclasses import asdict
from typing import Any, Dict, List

from sok.core.history import HistoryStore, Operation, UndoReport
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


def describe(operation: Operation) -> Dict[str, Any]:
    """An operation as the History page shows it."""
    return {
        "id": operation.id,
        "date": operation.date,
        "kind": operation.kind,
        "media_type": MEDIA_TYPE_OF_KIND.get(operation.kind, ""),
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
