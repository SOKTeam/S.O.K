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
"""The renames of S.O.K Server: the Ready rows of a tab go to their folder.

A rename takes the rows of one tab, all those that are Ready (or picked by
hand) or a list of them, and runs in the background like an analysis, never
at the same time as one. The file operations of the desktop batches move
them, with the file mode, the behavior settings, the subtitles and the
posters of the settings; the whole rename is one operation of the history.

With hard links, every source and destination of the rename are tested
first: if one pair cannot be linked, nothing is renamed and the error says
which folders. The files renamed leave the table; a file that fails, or is
skipped as a duplicate, stays on its row with why.
"""

import asyncio
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sok.config.config_manager import ConfigManager
from sok.core.batch import STATUS_READY
from sok.core.history import LINK, MOVE, content_kind, record
from sok.file_operations.artwork import save_artwork
from sok.file_operations.base_operations import can_hard_link
from sok.server.db import Database
from sok.server.events import EventBus
from sok.server.history import History
from sok.server.jobs import RENAME, Busy, Jobs
from sok.server.notify import Notifier
from sok.server.search import Searcher
from sok.server.settings import (
    DIFFERENT_DRIVES,
    MEDIA_TYPES,
    MISSING_FOLDER,
    NO_HARD_LINKS,
)

logger = logging.getLogger(__name__)

# State of a rename (renames.status).
RUNNING = "running"
DONE = "done"
FAILED = "failed"
INTERRUPTED = "interrupted"

# Why a file stayed on its row (rows.errors).
ALREADY_EXISTS = "already_exists"
RENAME_FAILED = "failed"


class RenameError(Exception):
    """A rename that cannot start: unknown_type, nothing_to_rename,
    no_destination, scan_running, already_running, or a hard link problem
    (different_drives, no_hard_links, missing_folder) with the folders."""

    def __init__(self, code: str, **details: str) -> None:
        super().__init__(code)
        self.code = code
        self.details = details

    def detail(self) -> Dict[str, str]:
        return {"code": self.code, **self.details}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def link_problem(file: str, folder: str) -> Optional[str]:
    """Why a file cannot be hard linked into a folder, or None."""
    try:
        same_device = os.stat(file).st_dev == os.stat(folder).st_dev
    except OSError:
        return MISSING_FOLDER
    if not same_device:
        return DIFFERENT_DRIVES
    if not can_hard_link(file, folder):
        return NO_HARD_LINKS
    return None


class Renamer:
    """Start the renames and keep their results in the database."""

    def __init__(
        self,
        db: Database,
        config: ConfigManager,
        events: EventBus,
        searcher: Searcher,
        history: History,
        jobs: Jobs,
        notifier: Optional[Notifier] = None,
    ) -> None:
        self._db = db
        self._config = config
        self._events = events
        self._searcher = searcher
        self._history = history
        self._jobs = jobs
        self._notifier = notifier
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._progress: Optional[Dict[str, int]] = None
        with db.transaction() as conn:
            # The server stopped during a rename.
            conn.execute(
                "UPDATE renames SET status = ?, finished = ? WHERE status = ?",
                (INTERRUPTED, _now(), RUNNING),
            )

    def start(
        self,
        media_type: str,
        row_ids: Optional[List[int]] = None,
        auto: bool = False,
    ) -> int:
        """Start renaming the Ready rows of a tab, in the background.

        Args:
            media_type: The tab: movies, tv, music, books or games.
            row_ids: Only these rows; all the Ready rows of the tab when None.
                The rows not Ready are left out.
            auto: Started by the automatic sorting (Watcher), not by a click.

        Returns:
            The id of the rename.

        Raises:
            RenameError: See its codes.
        """
        if media_type not in MEDIA_TYPES:
            raise RenameError("unknown_type")
        try:
            self._jobs.check(RENAME)
        except Busy as exc:
            raise RenameError(exc.code) from exc
        rows = self._ready_rows(media_type, row_ids)
        if not rows:
            raise RenameError("nothing_to_rename")
        if self._searcher.destination(rows[0]) is None:
            raise RenameError("no_destination")
        if self._config.get("file_mode", MOVE) == LINK:
            self._check_links(rows)
        with self._db.transaction() as conn:
            rename_id = conn.execute(
                "INSERT INTO renames (media_type, started, status, auto)"
                " VALUES (?, ?, ?, ?)",
                (media_type, _now(), RUNNING, int(auto)),
            ).lastrowid
        assert rename_id is not None
        self._loop = asyncio.get_running_loop()
        self._jobs.start(
            RENAME, self._run(rename_id, media_type, [r["id"] for r in rows])
        )
        self._publish()
        return rename_id

    def _ready_rows(self, media_type: str, row_ids: Optional[List[int]]) -> List[Any]:
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM rows WHERE media_type = ? AND status = ?"
                " AND selected IS NOT NULL ORDER BY id",
                (media_type, STATUS_READY),
            ).fetchall()
        if row_ids is not None:
            wanted = set(row_ids)
            rows = [row for row in rows if row["id"] in wanted]
        return rows

    def _check_links(self, rows: List[Any]) -> None:
        """Test a hard link for each drive of the files and each destination.

        Raises:
            RenameError: The first pair that cannot be linked.
        """
        tested = set()
        for row in rows:
            destination = self._searcher.destination(row)
            assert destination is not None
            for file in json.loads(row["files"]):
                try:
                    device = os.stat(file).st_dev
                except OSError:
                    # A file gone since the analysis fails on its own row.
                    continue
                if (device, destination) in tested:
                    continue
                tested.add((device, destination))
                problem = link_problem(file, destination)
                if problem:
                    raise RenameError(
                        problem,
                        source=str(Path(file).parent),
                        destination=destination,
                    )

    # ------------------------------------------------------------ Running

    async def _run(self, rename_id: int, media_type: str, row_ids: List[int]) -> None:
        try:
            with self._db.transaction() as conn:
                conn.executemany(
                    "UPDATE rows SET errors = NULL WHERE id = ?",
                    [(row_id,) for row_id in row_ids],
                )
                rows = [
                    conn.execute(
                        "SELECT * FROM rows WHERE id = ?", (row_id,)
                    ).fetchone()
                    for row_id in row_ids
                ]
            plans = [self._plan(row) for row in rows if row is not None]
            result = await asyncio.to_thread(self._rename, media_type, plans)
            self._apply(plans, result)
        except Exception as exc:  # noqa: BLE001 - the rename must end
            logger.exception("Rename %s failed", rename_id, exc_info=exc)
            self._finish(
                rename_id, FAILED, {"code": "failed", "message": str(exc)[:500]}
            )
            return
        self._finish(rename_id, DONE, None, result)
        if self._notifier is not None and result["moved"]:
            with self._db.transaction() as conn:
                auto = conn.execute(
                    "SELECT auto FROM renames WHERE id = ?", (rename_id,)
                ).fetchone()["auto"]
            self._notifier.renamed_later(
                {
                    "media_type": media_type,
                    "auto": bool(auto),
                    "renamed": len(result["moved"]),
                    "files": [
                        {"from": str(m["from"]), "to": str(m["to"])}
                        for m in result["moved"]
                    ],
                }
            )

    def _plan(self, row: Any) -> Tuple[Any, Any, str, List[Path]]:
        """(row, media item, destination, files) of a row to rename."""
        destination = self._searcher.destination(row)
        assert destination is not None
        files = [Path(f) for f in json.loads(row["files"])]
        return row, self._searcher.media_item(row), destination, files

    def _rename(
        self, media_type: str, plans: List[Tuple[Any, Any, str, List[Path]]]
    ) -> Dict[str, Any]:
        """Rename the files of the rows, as one operation of the history.

        Runs in a thread: the file operations block.
        """
        total = sum(len(files) for _, item, _, files in plans if item is not None)
        done_before = 0

        def progress(current: int, _total: int, _name: str) -> None:
            self._set_progress(done_before + current, total)

        reports: List[Dict[str, Any]] = []
        mappings_by_dest: Dict[str, List[Tuple[Path, Any]]] = defaultdict(list)
        for _, item, destination, files in plans:
            if item is not None:
                mappings_by_dest[destination].extend((f, item) for f in files)
        first = next((item for _, item, _, _ in plans if item is not None), None)
        ops = self._searcher.batch_ops(media_type)
        with record(content_kind(first), store=self._history) as journal:
            for destination, mappings in mappings_by_dest.items():
                start = len(reports)
                if media_type == "movies":
                    batches = [(mappings, ops.organize_movies_batch)]
                elif media_type == "tv":
                    # One series at a time, with its own folder.
                    batches = [
                        ([(f, item) for f in files], _series_organizer(ops, item))
                        for item, files in _by_item(mappings)
                    ]
                else:
                    batches = [(mappings, ops.organize_items_batch)]
                for batch, organize in batches:
                    report = organize(batch, destination, progress_callback=progress)
                    _spread_errors(report, [f for f, _ in batch])
                    reports.append(report)
                    done_before += len(batch)
                moved = [m for r in reports[start:] for m in r.get("moved", [])]
                if self._config.get("download_posters") and moved:
                    save_artwork(mappings, moved, destination)
        return {
            "moved": [m for r in reports for m in r.get("moved", [])],
            "subtitles": [s for r in reports for s in r.get("subtitles", [])],
            "skipped": [s for r in reports for s in r.get("skipped", [])],
            "errors": [e for r in reports for e in r.get("errors", [])],
            "operation": journal.operation_id,
        }

    def _apply(
        self, plans: List[Tuple[Any, Any, str, List[Path]]], result: Dict[str, Any]
    ) -> None:
        """The files renamed leave their row; the others keep why they stayed.

        A row left without files is removed.
        """
        moved = {m["from"] for m in result["moved"]}
        why: Dict[str, Dict[str, str]] = {}
        for skipped in result["skipped"]:
            why[skipped["file"]] = {
                "code": ALREADY_EXISTS,
                "message": skipped.get("reason", ""),
            }
        for error in result["errors"]:
            why[error["file"]] = {"code": RENAME_FAILED, "message": error["error"]}
        with self._db.transaction() as conn:
            for row, _item, _dest, files in plans:
                left = [str(f) for f in files if str(f) not in moved]
                if not left:
                    conn.execute("DELETE FROM rows WHERE id = ?", (row["id"],))
                    continue
                errors = {
                    path: why.get(path, {"code": RENAME_FAILED, "message": ""})
                    for path in left
                }
                conn.execute(
                    "UPDATE rows SET files = ?, errors = ? WHERE id = ?",
                    (json.dumps(left), json.dumps(errors), row["id"]),
                )

    def _set_progress(self, done: int, total: int) -> None:
        """Called from the thread of the rename."""
        self._progress = {"done": done, "total": total}
        event = {"type": "progress", "phase": "rename", **self._progress}
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._events.publish, event)

    def _finish(
        self,
        rename_id: int,
        status: str,
        error: Optional[Dict[str, str]],
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._progress = None
        summary = None
        if result is not None:
            summary = {
                "renamed": len(result["moved"]),
                "subtitles": len(result["subtitles"]),
                "skipped": result["skipped"],
                "errors": result["errors"],
                "operation": result["operation"],
            }
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE renames SET status = ?, finished = ?, error = ?, result = ?"
                " WHERE id = ?",
                (
                    status,
                    _now(),
                    json.dumps(error) if error else None,
                    json.dumps(summary) if summary else None,
                    rename_id,
                ),
            )
        self._publish()

    def _publish(self) -> None:
        self._events.publish({"type": "rename", **self.current()})

    # ------------------------------------------------------------ Reading

    def current(self) -> Dict[str, Any]:
        """The last rename, with its result once done."""
        with self._db.transaction() as conn:
            rename = conn.execute(
                "SELECT * FROM renames ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if rename is None:
            return {"rename": None}
        return {
            "rename": {
                "id": rename["id"],
                "media_type": rename["media_type"],
                "status": rename["status"],
                "started": rename["started"],
                "finished": rename["finished"],
                "auto": bool(rename["auto"]),
                "error": json.loads(rename["error"]) if rename["error"] else None,
                "result": json.loads(rename["result"]) if rename["result"] else None,
                "progress": self._progress if rename["status"] == RUNNING else None,
            }
        }


def _by_item(
    mappings: List[Tuple[Path, Any]],
) -> List[Tuple[Any, List[Path]]]:
    """The files of each media item, in order: one series at a time."""
    groups: Dict[int, Tuple[Any, List[Path]]] = {}
    for file, item in mappings:
        groups.setdefault(id(item), (item, []))[1].append(file)
    return list(groups.values())


def _series_organizer(ops: Any, item: Any) -> Any:
    """organize_files_list for the files of one series, called like the
    batches of the other media types."""

    def organize(
        mappings: List[Tuple[Path, Any]], destination: str, **kwargs: Any
    ) -> Dict[str, Any]:
        return ops.organize_files_list(
            [f for f, _ in mappings], destination, item, **kwargs
        )

    return organize


def _spread_errors(report: Dict[str, Any], files: List[Path]) -> None:
    """Give an error of a whole batch, such as a series folder that cannot be
    created, to each of its files not renamed."""
    sources = {str(f) for f in files}
    moved = {m["from"] for m in report.get("moved", [])}
    errors = []
    for error in report.get("errors", []):
        if error["file"] in sources:
            errors.append(error)
        else:
            errors.extend(
                {"file": source, "error": error["error"]}
                for source in sorted(sources - moved)
            )
    report["errors"] = errors
