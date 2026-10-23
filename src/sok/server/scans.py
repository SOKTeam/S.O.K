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
"""The analyses of S.O.K Server: scan the source folders, sort the files,
search them.

An analysis runs in the background, one at a time. The type detector of the
desktop home page (MediaTypeDetector) sorts the files of the source folders;
each item becomes a row of the table of its media type:

- one row per movie, track, book or game (the .cue and .bin of a game are
  one item);
- one row per series, its episodes being its files, and one per album.

A new analysis keeps the rows it finds again, with the choices made on them
(search text, match, destination): a series or an album keeps them when
episodes or tracks are added. The rows whose files are gone are removed.
The files whose type is a guess are "to check", until the user confirms a
type, which the next analyses remember. The files already processed (renamed
before, with the same size and date) are left out and counted.

Then the rows not searched yet are searched (Searcher), kind by kind. A
missing key or a used quota stops the media types of that service, with the
rows sorted; the error of the analysis says which key.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sok.core.batch import group_game_files
from sok.core.interfaces import ContentType
from sok.core.utils import natural_key
from sok.file_operations.detection import (
    DetectedFile,
    DetectionReport,
    MediaTypeDetector,
)
from sok.server.db import Database
from sok.server.events import EventBus
from sok.server.history import unchanged
from sok.server.jobs import SCAN, Busy, Jobs
from sok.server.search import Searcher, SearchStopped, search_error
from sok.server.settings import MEDIA_TYPES, Settings

logger = logging.getLogger(__name__)

# State of an analysis (scans.status).
RUNNING = "running"
DONE = "done"
FAILED = "failed"
# The server stopped during the analysis.
INTERRUPTED = "interrupted"

# Status of a row that was not searched yet; the others are those of the
# batch engine (ok, ambiguous, missing).
PENDING = "pending"
ROW_STATUSES = (PENDING, "ok", "ambiguous", "missing")

MEDIA_TYPE_OF = {
    ContentType.MOVIE: "movies",
    ContentType.EPISODE: "tv",
    ContentType.ALBUM: "music",
    ContentType.TRACK: "music",
    ContentType.BOOK: "books",
    ContentType.GAME: "games",
}
# Kinds that group several files in one row.
GROUP_KINDS = (ContentType.EPISODE, ContentType.ALBUM)


class ScanError(Exception):
    """An analysis that cannot start: already_running, rename_running or
    no_sources."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class UnknownFile(ValueError):
    """A file that is not to check."""


@dataclass
class RowDraft:
    """A row as an analysis finds it, before the database."""

    key: str
    kind: ContentType
    title: Optional[str]
    files: List[str]

    @property
    def media_type(self) -> str:
        return MEDIA_TYPE_OF[self.kind]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def drafts_from_report(report: DetectionReport) -> List[RowDraft]:
    """The rows of the groups of a detection report."""
    drafts: List[RowDraft] = []
    for group in report.groups:
        if group.kind in GROUP_KINDS:
            drafts.append(
                RowDraft(
                    f"{group.kind.value}:{group.key}",
                    group.kind,
                    group.title,
                    [str(f) for f in group.files],
                )
            )
        elif group.kind == ContentType.GAME:
            for files in group_game_files(list(group.files)):
                drafts.append(
                    RowDraft(
                        f"game:{files[0]}",
                        group.kind,
                        None,
                        [str(f) for f in files],
                    )
                )
        else:
            for file in group.files:
                drafts.append(
                    RowDraft(
                        f"{group.kind.value}:{file}", group.kind, None, [str(file)]
                    )
                )
    return drafts


def _apply_choices(
    detector: MediaTypeDetector, report: DetectionReport, choices: Dict[str, str]
) -> None:
    """Give the files to check the type the user confirmed before."""
    for item in list(report.to_check):
        kind = choices.get(str(item.path))
        if kind:
            detector.confirm(report, item, ContentType(kind))


class Scans:
    """Start the analyses and keep their results in the database."""

    def __init__(
        self,
        db: Database,
        settings: Settings,
        events: EventBus,
        searcher: Searcher,
        jobs: Jobs,
    ) -> None:
        self._db = db
        self._settings = settings
        self._events = events
        self._searcher = searcher
        self._jobs = jobs
        # Phase of the running analysis (detect, search) and its progress.
        self._progress: Optional[Dict[str, Any]] = None
        with db.transaction() as conn:
            # The server stopped during an analysis.
            conn.execute(
                "UPDATE scans SET status = ?, finished = ? WHERE status = ?",
                (INTERRUPTED, _now(), RUNNING),
            )

    def start(self) -> int:
        """Start an analysis of the source folders, in the background.

        Returns:
            The id of the analysis.

        Raises:
            ScanError: already_running, rename_running, or no_sources when
                no source folder is set.
        """
        try:
            self._jobs.check(SCAN)
        except Busy as exc:
            raise ScanError(exc.code) from exc
        sources = self._settings.folders()["sources"]
        if not sources:
            raise ScanError("no_sources")
        with self._db.transaction() as conn:
            scan_id = conn.execute(
                "INSERT INTO scans (started, status) VALUES (?, ?)",
                (_now(), RUNNING),
            ).lastrowid
        assert scan_id is not None
        self._jobs.start(SCAN, self._run(scan_id, sources))
        self._publish()
        return scan_id

    async def _run(self, scan_id: int, sources: List[str]) -> None:
        missing = [s for s in sources if not os.path.isdir(s)]
        try:
            with self._db.transaction() as conn:
                choices = {
                    row["path"]: row["kind"]
                    for row in conn.execute("SELECT path, kind FROM type_choices")
                }
                processed = {
                    row["path"]: (row["size"], row["mtime_ns"])
                    for row in conn.execute("SELECT * FROM processed")
                }
            self._set_progress("detect", 0, 0)
            report, skipped = await asyncio.to_thread(
                self._detect,
                [s for s in sources if s not in missing],
                choices,
                processed,
            )
            with self._db.transaction() as conn:
                conn.execute(
                    "UPDATE scans SET processed = ? WHERE id = ?", (skipped, scan_id)
                )
            self._save(report)
            self._set_progress("search", 0, 0)
            await self._searcher.search_pending(
                lambda done, total: self._set_progress("search", done, total)
            )
        except SearchStopped as exc:
            self._finish(scan_id, FAILED, search_error(exc), missing)
            return
        except Exception as exc:  # noqa: BLE001 - the analysis must end
            logger.exception("Analysis %s failed", scan_id, exc_info=exc)
            self._finish(
                scan_id, FAILED, {"code": "failed", "message": str(exc)[:500]}, missing
            )
            return
        self._finish(scan_id, DONE, None, missing)

    def _set_progress(self, phase: str, done: int, total: int) -> None:
        self._progress = {"phase": phase, "done": done, "total": total}
        self._events.publish({"type": "progress", **self._progress})

    @staticmethod
    def _detect(
        sources: List[str],
        choices: Dict[str, str],
        processed: Dict[str, Tuple[int, int]],
    ) -> Tuple[DetectionReport, int]:
        """Sort the files of the sources, without those already processed.

        Returns:
            The report, and how many files were left out as processed.
        """
        detector = MediaTypeDetector()
        report = detector.detect_sources([Path(s) for s in sources])
        _apply_choices(detector, report, choices)

        def done(path: Path) -> bool:
            known = processed.get(str(path))
            return known is not None and unchanged(str(path), *known)

        skipped = 0
        for group in report.groups:
            kept = [f for f in group.files if not done(f)]
            skipped += len(group.files) - len(kept)
            group.files = kept
        report.groups = [g for g in report.groups if g.files]
        kept_items = [d for d in report.to_check if not done(d.path)]
        skipped += len(report.to_check) - len(kept_items)
        report.to_check = kept_items
        return report, skipped

    def _save(self, report: DetectionReport) -> None:
        """Replace the rows and the files to check with those of a report.

        The rows found again keep their search, match and destination.
        """
        drafts = drafts_from_report(report)
        keys = [d.key for d in drafts]
        with self._db.transaction() as conn:
            existing = {
                row["key"]: row for row in conn.execute("SELECT key, files FROM rows")
            }
            for draft in drafts:
                files = json.dumps(draft.files)
                if draft.key in existing:
                    conn.execute(
                        "UPDATE rows SET files = ?, title = ? WHERE key = ?",
                        (files, draft.title, draft.key),
                    )
                else:
                    conn.execute(
                        "INSERT INTO rows (key, media_type, kind, title, files, status)"
                        " VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            draft.key,
                            draft.media_type,
                            draft.kind.value,
                            draft.title,
                            files,
                            PENDING,
                        ),
                    )
            gone = [key for key in existing if key not in set(keys)]
            conn.executemany("DELETE FROM rows WHERE key = ?", [(k,) for k in gone])
            conn.execute("DELETE FROM to_check")
            conn.executemany(
                "INSERT INTO to_check (path, kind, title, reason) VALUES (?, ?, ?, ?)",
                [
                    (str(d.path), d.kind.value, d.title, d.reason)
                    for d in report.to_check
                ],
            )

    def _finish(
        self,
        scan_id: int,
        status: str,
        error: Optional[Dict[str, str]],
        missing: List[str],
    ) -> None:
        self._progress = None
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE scans SET status = ?, finished = ?, error = ?,"
                " missing_sources = ? WHERE id = ?",
                (
                    status,
                    _now(),
                    json.dumps(error) if error else None,
                    json.dumps(missing),
                    scan_id,
                ),
            )
        self._publish()

    def _publish(self) -> None:
        self._events.publish({"type": "scan", **self.summary()})

    # ------------------------------------------------------------ Reading

    def summary(self) -> Dict[str, Any]:
        """The last analysis, the rows per media type and status, the files
        to check."""
        with self._db.transaction() as conn:
            scan = conn.execute(
                "SELECT * FROM scans ORDER BY id DESC LIMIT 1"
            ).fetchone()
            counts = {
                media_type: {status: 0 for status in ROW_STATUSES}
                for media_type in MEDIA_TYPES
            }
            for row in conn.execute(
                "SELECT media_type, status, COUNT(*) AS n FROM rows"
                " GROUP BY media_type, status"
            ):
                counts[row["media_type"]][row["status"]] = row["n"]
            to_check = [
                {
                    "path": row["path"],
                    "kind": row["kind"],
                    "media_type": MEDIA_TYPE_OF[ContentType(row["kind"])],
                    "title": row["title"],
                    "reason": row["reason"],
                }
                for row in conn.execute("SELECT * FROM to_check ORDER BY path")
            ]
        for media_type in counts.values():
            media_type["total"] = sum(media_type[s] for s in ROW_STATUSES)
        return {
            "scan": None
            if scan is None
            else {
                "id": scan["id"],
                "status": scan["status"],
                "started": scan["started"],
                "finished": scan["finished"],
                "error": json.loads(scan["error"]) if scan["error"] else None,
                "missing_sources": json.loads(scan["missing_sources"]),
                # Files left out: renamed before, unchanged since.
                "processed": scan["processed"],
                "progress": self._progress if scan["status"] == RUNNING else None,
            },
            "counts": counts,
            "to_check": to_check,
        }

    # -------------------------------------------------------- To check

    async def confirm(self, path: str, kind: ContentType) -> Optional[Dict[str, Any]]:
        """Give a file to check its type: it joins the rows of that type.

        The choice is remembered for the next analyses. A new row is searched
        at once, as the rows of an analysis.

        Returns:
            Why the search stopped (search_error), or None.

        Raises:
            UnknownFile: The file is not to check.
        """
        with self._db.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM to_check WHERE path = ?", (path,)
            ).fetchone()
            if row is None:
                raise UnknownFile(path)
            item = DetectedFile(
                Path(path), ContentType(row["kind"]), row["title"], False, row["reason"]
            )
            report = DetectionReport(to_check=[item])
            MediaTypeDetector().confirm(report, item, kind)
            draft = drafts_from_report(report)[0]
            existing = conn.execute(
                "SELECT files FROM rows WHERE key = ?", (draft.key,)
            ).fetchone()
            if existing:
                # A series or an album that is already a row gets the file.
                files = json.loads(existing["files"])
                if path not in files:
                    files.append(path)
                conn.execute(
                    "UPDATE rows SET files = ? WHERE key = ?",
                    (
                        json.dumps(sorted(files, key=lambda f: natural_key(Path(f)))),
                        draft.key,
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO rows (key, media_type, kind, title, files, status)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        draft.key,
                        draft.media_type,
                        kind.value,
                        draft.title,
                        json.dumps(draft.files),
                        PENDING,
                    ),
                )
            conn.execute("DELETE FROM to_check WHERE path = ?", (path,))
            conn.execute(
                "INSERT OR REPLACE INTO type_choices (path, kind) VALUES (?, ?)",
                (path, kind.value),
            )
            row = conn.execute(
                "SELECT id, status FROM rows WHERE key = ?", (draft.key,)
            ).fetchone()
        self._publish()
        if row["status"] != PENDING:
            return None
        try:
            await self._searcher.search_row(row["id"])
        except SearchStopped as exc:
            # The row stays "not searched": its search button tries again.
            return search_error(exc)
        finally:
            self._publish()
        return None
