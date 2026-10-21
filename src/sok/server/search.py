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
"""The search of the rows of S.O.K Server, and what the tabs show of them.

The batch engine of the desktop app (BatchMatcher) searches each row: a
movie by its file name, a series by its title. A series that is Ready, or
picked by hand, gets its details and the titles of its episodes, which
name the episodes. A missing key or a used quota stops the search
(SearchStopped); the rows keep what they had.
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sok.config.config_manager import ConfigManager
from sok.core.batch import (
    STATUS_READY,
    BatchMatch,
    BatchMatcher,
    candidate_year,
    parse_movie,
    parse_series,
)
from sok.core.exceptions import APIAuthenticationError, APIError, APIRateLimitError
from sok.core.interfaces import ContentType, MediaType
from sok.core.media_manager import get_media_manager
from sok.core.series import fetch_episode_titles
from sok.file_operations.video_operations import VideoFileOperations
from sok.media.factory import create_media_item
from sok.server.db import Database

logger = logging.getLogger(__name__)

# What each searched media type looks for: content type, name reader, and
# the type of create_media_item.
SEARCHED = {
    "movies": (ContentType.MOVIE, parse_movie, "movie"),
    "tv": (ContentType.TV_SERIES, parse_series, "tv"),
}

# Why a search stopped (SearchStopped.code).
MISSING_KEY = "missing_key"
KEY_REFUSED = "key_refused"
RATE_LIMITED = "rate_limited"

# Length of the overview of a candidate in the answers.
OVERVIEW_LENGTH = 300


class SearchStopped(Exception):
    """A search that cannot go on: a missing or refused key, a used quota."""

    def __init__(self, code: str, service: str) -> None:
        super().__init__(f"{code}: {service}")
        self.code = code
        self.service = service


class UnknownRow(LookupError):
    """No row has this id."""


class InvalidChange(ValueError):
    """A change of a row that cannot be: invalid_selection, invalid_destination."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def api_language(language: str) -> str:
    """The language of the results: "fr" → "fr-FR", as the desktop app asks."""
    return f"{language}-{language.upper()}" if len(language) == 2 else language


class Searcher:
    """Search the rows, change them, and describe them for the tabs."""

    def __init__(self, db: Database, config: ConfigManager) -> None:
        self._db = db
        self._config = config
        self._ops = VideoFileOperations()

    @property
    def _language(self) -> str:
        return api_language(self._config.get("language", "en") or "en")

    def _manager(self, media_type: str) -> Any:
        """The media manager, once sure it has an API for the media type."""
        manager = get_media_manager()
        if not manager.get_available_apis_for_media_type(MediaType.VIDEO):
            raise SearchStopped(MISSING_KEY, "tmdb")
        return manager

    # ------------------------------------------------------------ Search

    async def search_pending(
        self, progress: Optional[Callable[[int, int], None]] = None
    ) -> int:
        """Search every row not searched yet, movies then series.

        Args:
            progress: Called with (done, total) after each row.

        Returns:
            The number of rows searched.

        Raises:
            SearchStopped: A key is missing or refused, or the quota is used.
        """
        with self._db.transaction() as conn:
            pending = conn.execute(
                "SELECT id, media_type, files FROM rows WHERE status = 'pending'"
                " AND media_type IN ('movies', 'tv') ORDER BY media_type, id"
            ).fetchall()
        total = len(pending)
        done = 0
        for media_type in SEARCHED:
            rows = [r for r in pending if r["media_type"] == media_type]
            if not rows:
                continue
            matcher = self._matcher(media_type)

            def report(_done: int, _total: int, _file: Path) -> None:
                nonlocal done
                done += 1
                if progress:
                    progress(done, total)

            items = [[Path(f) for f in json.loads(r["files"])] for r in rows]
            matches = await self._run(matcher.match_all(items, report))
            for row, match in zip(rows, matches):
                await self._save_match(row["id"], media_type, match)
        return total

    async def search_row(self, row_id: int, query: Optional[str] = None) -> None:
        """Search one row again, with the text typed or its own text.

        Raises:
            UnknownRow: No row has this id.
            SearchStopped: A key is missing or refused, or the quota is used.
        """
        row = self._row(row_id)
        media_type = row["media_type"]
        if media_type not in SEARCHED:
            raise InvalidChange("not_searched")
        files = [Path(f) for f in json.loads(row["files"])]
        text = (query or "").strip() or None
        match = await self._run(self._matcher(media_type).match(files, text))
        await self._save_match(row_id, media_type, match)

    def _matcher(self, media_type: str) -> BatchMatcher:
        content_type, parse, _factory = SEARCHED[media_type]
        return BatchMatcher(
            self._manager(media_type), content_type, parse, self._language
        )

    @staticmethod
    async def _run(awaitable: Any) -> Any:
        """Await a search; a key or quota problem stops it."""
        try:
            return await awaitable
        except APIAuthenticationError as exc:
            raise SearchStopped(KEY_REFUSED, exc.api_name.lower()) from exc
        except APIRateLimitError as exc:
            raise SearchStopped(RATE_LIMITED, exc.api_name.lower()) from exc

    async def _save_match(
        self, row_id: int, media_type: str, match: BatchMatch
    ) -> None:
        details = None
        if (
            media_type == "tv"
            and match.status == STATUS_READY
            and match.selected is not None
        ):
            details = await self._series_details(match.candidates[match.selected])
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE rows SET query = ?, year = ?, candidates = ?, selected = ?,"
                " status = ?, details = ? WHERE id = ?",
                (
                    match.query,
                    match.year,
                    json.dumps(match.candidates),
                    match.selected,
                    match.status,
                    json.dumps(details) if details else None,
                    row_id,
                ),
            )

    async def _series_details(self, candidate: Dict[str, Any]) -> Optional[Dict]:
        """The seasons and the episode titles of a series; None if they fail."""
        manager = self._manager("tv")
        series_id = str(candidate.get("id"))
        try:
            details = await manager.get_details(
                series_id, ContentType.TV_SERIES, language=self._language
            )
            episodes = await fetch_episode_titles(
                manager.get_current_api(MediaType.VIDEO),
                series_id,
                details.get("number_of_seasons") or 0,
                self._language,
            )
        except APIError as exc:
            logger.warning("Details failed for series %s: %s", series_id, exc)
            return None
        return {
            "id": series_id,
            "number_of_seasons": details.get("number_of_seasons") or 0,
            "seasons": [
                {"season_number": s.get("season_number"), "name": s.get("name")}
                for s in details.get("seasons", [])
            ],
            "episodes": episodes,
        }

    # ------------------------------------------------------------ Change

    async def change(
        self,
        row_id: int,
        selected: Optional[int] = None,
        destination: Optional[int] = None,
        destinations: int = 1,
    ) -> None:
        """Pick a candidate (the row is then Ready) or a destination folder.

        Args:
            row_id: The row.
            selected: Index of the candidate picked.
            destination: Index of the destination folder of its media type.
            destinations: How many destination folders the media type has.

        Raises:
            UnknownRow: No row has this id.
            InvalidChange: invalid_selection or invalid_destination.
        """
        row = self._row(row_id)
        candidates = json.loads(row["candidates"])
        if selected is not None and not 0 <= selected < len(candidates):
            raise InvalidChange("invalid_selection")
        if destination is not None and not 0 <= destination < max(destinations, 1):
            raise InvalidChange("invalid_destination")

        details = row["details"]
        if selected is not None and row["media_type"] == "tv":
            current = json.loads(details) if details else None
            wanted = str(candidates[selected].get("id"))
            if not current or current.get("id") != wanted:
                found = await self._series_details(candidates[selected])
                details = json.dumps(found) if found else None
        with self._db.transaction() as conn:
            if selected is not None:
                conn.execute(
                    "UPDATE rows SET selected = ?, status = ?, details = ? WHERE id = ?",
                    (selected, STATUS_READY, details, row_id),
                )
            if destination is not None:
                conn.execute(
                    "UPDATE rows SET destination = ? WHERE id = ?",
                    (destination, row_id),
                )

    # ---------------------------------------------------------- Reading

    def _row(self, row_id: int) -> Any:
        with self._db.transaction() as conn:
            row = conn.execute("SELECT * FROM rows WHERE id = ?", (row_id,)).fetchone()
        if row is None:
            raise UnknownRow(row_id)
        return row

    def rows(self, media_type: str) -> List[Dict[str, Any]]:
        """The rows of a tab, as the interface shows them."""
        with self._db.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM rows WHERE media_type = ? ORDER BY id", (media_type,)
            ).fetchall()
        return [self.describe(row) for row in rows]

    def row(self, row_id: int) -> Dict[str, Any]:
        return self.describe(self._row(row_id))

    def describe(self, row: Any) -> Dict[str, Any]:
        """A row with its candidates and, once matched, the new names."""
        candidates = json.loads(row["candidates"])
        selected = row["selected"]
        details = json.loads(row["details"]) if row["details"] else None
        files = json.loads(row["files"])
        names = self._new_names(row["media_type"], files, candidates, selected, details)
        return {
            "id": row["id"],
            "media_type": row["media_type"],
            "kind": row["kind"],
            "title": row["title"],
            "query": row["query"],
            "year": row["year"],
            "status": row["status"],
            "selected": selected,
            "destination": row["destination"],
            "candidates": [_candidate(c) for c in candidates],
            "files": [
                {"path": path, "name": Path(path).name, "new_name": name}
                for path, name in zip(files, names)
            ],
            "episodes_found": len(details["episodes"]) if details else None,
        }

    def _new_names(
        self,
        media_type: str,
        files: List[str],
        candidates: List[Dict[str, Any]],
        selected: Optional[int],
        details: Optional[Dict[str, Any]],
    ) -> List[Optional[str]]:
        """The new name of each file, or None before a match."""
        if media_type not in SEARCHED or selected is None or not candidates:
            return [None] * len(files)
        candidate = dict(candidates[selected])
        if details:
            candidate["episodes"] = details["episodes"]
        item = create_media_item(
            candidate,
            SEARCHED[media_type][2],
            get_media_manager(),
            language=self._config.get("language", "en") or "en",
        )
        if item is None:
            return [None] * len(files)
        return [self._ops.generate_new_filename(item, Path(f).name) for f in files]


def _candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """What the interface shows of a search result."""
    overview = candidate.get("overview") or ""
    return {
        "id": candidate.get("id"),
        "title": candidate.get("title") or candidate.get("name"),
        "original_title": candidate.get("original_title")
        or candidate.get("original_name"),
        "year": candidate_year(candidate),
        "poster": candidate.get("poster_path") or candidate.get("image_url"),
        "overview": overview[:OVERVIEW_LENGTH],
    }


def search_error(exc: SearchStopped) -> Dict[str, str]:
    return {"code": exc.code, "service": exc.service}
