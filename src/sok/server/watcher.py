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
"""The automatic sorting of S.O.K Server: the source folders are watched,
and the new files are analyzed and renamed on their own.

When the auto_sort setting is on, the server looks at the files of the
source folders every auto_sort_minutes. It reads the folders again instead
of waiting for the events of the system, which most NAS shares and Docker
mounts do not send. A file is taken once it is finished: same size and same
date as at the check before, and not a download in progress (.part, .!qB,
.crdownload…).

When finished files are new (or changed) since the last automatic sorting,
an analysis runs, then the rows that are Ready are renamed, tab by tab, if
all their files are finished. The rows to pick, the missing ones and the
files to check wait in the tables. The analyses and renames it starts are
marked "auto"; the history can undo them like the others.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from sok.server.db import Database
from sok.server.events import EventBus
from sok.server.history import unchanged
from sok.server.jobs import Jobs
from sok.server.renames import RenameError, Renamer
from sok.server.scans import ScanError, Scans
from sok.server.settings import MEDIA_TYPES, SOURCES, Settings

logger = logging.getLogger(__name__)

# The endings of the files that a download client is still writing.
PARTIAL_SUFFIXES = (".part", ".partial", ".!qb", ".!ut", ".crdownload", ".download")

# Seconds between two looks at the clock: a change of auto_sort_minutes
# applies within this time.
TICK = 30

# The key of the last automatic sorting in the options table.
LAST_RUN = "auto_sort_last_run"

# (size, mtime_ns) of a file.
Signature = Tuple[int, int]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def snapshot(sources: List[str]) -> Dict[str, Signature]:
    """The files of the source folders with their size and date, without
    hidden files and downloads in progress."""
    files: Dict[str, Signature] = {}
    for source in sources:
        for root, dirs, names in os.walk(source):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in names:
                if name.startswith(".") or name.lower().endswith(PARTIAL_SUFFIXES):
                    continue
                path = os.path.join(root, name)
                try:
                    stat = os.stat(path)
                except OSError:
                    continue
                files[path] = (stat.st_size, stat.st_mtime_ns)
    return files


class Watcher:
    """Check the source folders and sort the new files, when auto_sort is on."""

    def __init__(
        self,
        db: Database,
        settings: Settings,
        scans: Scans,
        renamer: Renamer,
        jobs: Jobs,
        events: EventBus,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._db = db
        self._settings = settings
        self._scans = scans
        self._renamer = renamer
        self._jobs = jobs
        self._events = events
        self._clock = clock
        # The files at the last check, to see which ones are finished.
        self._previous: Dict[str, Signature] = {}
        # The finished files the last automatic sorting saw.
        self._seen: Dict[str, Signature] = {}
        self._last_check: Optional[float] = None
        self._last_check_date: Optional[str] = None

    async def run(self) -> None:
        """Check the folders forever, every auto_sort_minutes (the task of
        the server)."""
        while True:
            try:
                if self._due():
                    await self.check()
            except Exception as exc:  # noqa: BLE001 - the watch must go on
                logger.exception("Automatic sorting failed", exc_info=exc)
            await asyncio.sleep(TICK)

    def _due(self) -> bool:
        if not self._settings.value("auto_sort"):
            # Turned off: the next start begins again from nothing.
            self._previous = {}
            self._last_check = None
            return False
        minutes = self._settings.value("auto_sort_minutes")
        return (
            self._last_check is None or self._clock() - self._last_check >= minutes * 60
        )

    async def check(self) -> bool:
        """Look at the source folders once; sort the new finished files.

        Returns:
            Whether an automatic sorting ran.
        """
        if self._jobs.running():
            # An analysis or a rename by hand: the next tick tries again.
            return False
        self._last_check = self._clock()
        self._last_check_date = _now()
        sources = [s for s in self._settings.folders()[SOURCES] if os.path.isdir(s)]
        current = await asyncio.to_thread(snapshot, sources)
        finished = {
            path: signature
            for path, signature in current.items()
            if self._previous.get(path) == signature
        }
        self._previous = current
        new = [
            path
            for path, signature in finished.items()
            if self._seen.get(path) != signature and not self._processed(path)
        ]
        if not new:
            self._publish()
            return False
        logger.info("Automatic sorting: %d new files", len(new))
        self._seen.update(finished)
        await self._sort(set(finished))
        return True

    def _processed(self, path: str) -> bool:
        """Whether the file was renamed before and has not changed since."""
        with self._db.transaction() as conn:
            row = conn.execute(
                "SELECT size, mtime_ns FROM processed WHERE path = ?", (path,)
            ).fetchone()
        return row is not None and unchanged(path, row["size"], row["mtime_ns"])

    async def _sort(self, finished: Set[str]) -> None:
        """Analyze, then rename the Ready rows whose files are all finished."""
        run: Dict[str, Any] = {
            "date": _now(),
            "scan": None,
            "renamed": 0,
            "errors": [],
        }
        try:
            run["scan"] = self._scans.start(auto=True)
        except ScanError as exc:
            run["errors"].append({"code": exc.code})
            self._save(run)
            return
        await self._jobs.wait()
        error = self._scans.summary()["scan"]["error"]
        if error:
            # A missing key: the rows of the other services can be Ready.
            run["errors"].append(error)
        for media_type in MEDIA_TYPES:
            row_ids = self._ready_rows(media_type, finished)
            if not row_ids:
                continue
            try:
                self._renamer.start(media_type, row_ids, auto=True)
            except RenameError as exc:
                run["errors"].append({"media_type": media_type, **exc.detail()})
                continue
            await self._jobs.wait()
            rename = self._renamer.current()["rename"]
            if rename["result"]:
                run["renamed"] += rename["result"]["renamed"]
            if rename["error"]:
                run["errors"].append({"media_type": media_type, **rename["error"]})
        self._save(run)

    def _ready_rows(self, media_type: str, finished: Set[str]) -> List[int]:
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT id, files FROM rows WHERE media_type = ? AND status = 'ok'"
                " AND selected IS NOT NULL ORDER BY id",
                (media_type,),
            ).fetchall()
        return [
            row["id"]
            for row in rows
            if all(f in finished for f in json.loads(row["files"]))
        ]

    def _save(self, run: Dict[str, Any]) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO options (key, value) VALUES (?, ?)",
                (LAST_RUN, json.dumps(run)),
            )
        self._publish()

    def _publish(self) -> None:
        self._events.publish({"type": "watch", **self.status()})

    # ------------------------------------------------------------ Reading

    def status(self) -> Dict[str, Any]:
        """Whether the sorting is on, its last check and its last run."""
        with self._db.transaction() as conn:
            row = conn.execute(
                "SELECT value FROM options WHERE key = ?", (LAST_RUN,)
            ).fetchone()
        return {
            "enabled": self._settings.value("auto_sort"),
            "minutes": self._settings.value("auto_sort_minutes"),
            "last_check": self._last_check_date,
            "last_run": json.loads(row["value"]) if row else None,
        }
