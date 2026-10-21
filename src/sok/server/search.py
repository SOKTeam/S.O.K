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

The batch engine of the desktop app (BatchMatcher) searches each row, as
the batch pages of the desktop app do: a movie, a track, a book or a game
by its file name, a series by its title, an album by its tags or its
folder. A series that is Ready, or picked by hand, gets its details and
the titles of its episodes, which name the episodes. A missing key or a
used quota stops the search (SearchStopped); the rows keep what they had.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sok.config.config_manager import ConfigManager
from sok.core.batch import (
    STATUS_READY,
    BatchMatch,
    BatchMatcher,
    QueryParser,
    SameWork,
    candidate_year,
    parse_album,
    parse_book,
    parse_game,
    parse_movie,
    parse_series,
    parse_track,
    same_album,
    same_book,
    same_track,
)
from sok.core.exceptions import APIAuthenticationError, APIError, APIRateLimitError
from sok.core.interfaces import ContentType, MediaType
from sok.core.media_manager import get_media_manager
from sok.core.series import fetch_episode_titles
from sok.file_operations.book_operations import BookFileOperations
from sok.file_operations.game_operations import GameFileOperations
from sok.file_operations.music_operations import MusicFileOperations
from sok.file_operations.organize import FileListOrganizerMixin
from sok.file_operations.video_operations import VideoFileOperations
from sok.media.factory import create_media_item
from sok.server.db import Database

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Search:
    """How the rows of one kind are searched and named."""

    content_type: ContentType
    media_type: MediaType
    parse: QueryParser
    # The type of create_media_item.
    factory_type: str
    same_work: Optional[SameWork] = None
    # Results in the language of the settings; not for books, where it would
    # hide books in other languages, nor for music.
    localized: bool = True


# Each kind of row (rows.kind), as the batch pages of the desktop app search it.
SEARCHES: Dict[str, Search] = {
    "movie": Search(ContentType.MOVIE, MediaType.VIDEO, parse_movie, "movie"),
    "episode": Search(ContentType.TV_SERIES, MediaType.VIDEO, parse_series, "tv"),
    "album": Search(
        ContentType.ALBUM, MediaType.MUSIC, parse_album, "album", same_album, False
    ),
    "track": Search(
        ContentType.TRACK, MediaType.MUSIC, parse_track, "track", same_track, False
    ),
    "book": Search(
        ContentType.BOOK, MediaType.BOOK, parse_book, "book", same_book, False
    ),
    "game": Search(ContentType.GAME, MediaType.GAME, parse_game, "game"),
}

# The setting of the service searched for each media type, to name the key
# that is missing.
PREFERRED_API = {
    MediaType.VIDEO: ("preferred_api_video", "tmdb"),
    MediaType.MUSIC: ("preferred_api_music", "deezer"),
    MediaType.BOOK: ("preferred_api_books", "google_books"),
    MediaType.GAME: ("preferred_api_games", "igdb"),
}

# Why a search stopped (SearchStopped.code).
MISSING_KEY = "missing_key"
KEY_REFUSED = "key_refused"
RATE_LIMITED = "rate_limited"

# Length of the overview of a candidate in the answers.
OVERVIEW_LENGTH = 300


class SearchStopped(Exception):
    """A search that cannot go on: a missing or refused key, a used quota.

    After a search of several kinds, others lists the services that
    stopped after this one.
    """

    def __init__(self, code: str, service: str) -> None:
        super().__init__(f"{code}: {service}")
        self.code = code
        self.service = service
        self.others: List["SearchStopped"] = []


def service_id(api_name: str) -> str:
    """The id of a service from the name of its API class: GoogleBooks →
    google_books."""
    from sok.config.api_registry import get_all_services

    wanted = api_name.lower().replace("_", "")
    for service in get_all_services():
        if service.id.replace("_", "") == wanted:
            return service.id
    return api_name.lower()


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
        self._video = VideoFileOperations()
        self._batch_ops: Dict[str, FileListOrganizerMixin] = {
            "music": MusicFileOperations(),
            "books": BookFileOperations(),
            "games": GameFileOperations(),
        }

    @property
    def _language(self) -> str:
        return api_language(self._config.get("language", "en") or "en")

    def _manager(self, media_type: MediaType) -> Any:
        """The media manager, once sure it has an API for the media type."""
        manager = get_media_manager()
        if not manager.get_available_apis_for_media_type(media_type):
            setting, default = PREFERRED_API[media_type]
            raise SearchStopped(MISSING_KEY, self._config.get(setting) or default)
        return manager

    # ------------------------------------------------------------ Search

    async def search_pending(
        self, progress: Optional[Callable[[int, int], None]] = None
    ) -> int:
        """Search every row not searched yet, kind by kind.

        Args:
            progress: Called with (done, total) after each row.

        Returns:
            The number of rows searched.

        Raises:
            SearchStopped: A key is missing or refused, or the quota is used.
                The kinds of the other services are searched first: a used
                quota of Google Books does not keep the games from their
                search.
        """
        with self._db.transaction() as conn:
            pending = conn.execute(
                "SELECT id, kind, files FROM rows WHERE status = 'pending' ORDER BY id"
            ).fetchall()
        total = len(pending)
        done = 0
        stops: List[SearchStopped] = []
        stopped: set = set()
        for kind, search in SEARCHES.items():
            rows = [r for r in pending if r["kind"] == kind]
            if not rows or search.media_type in stopped:
                continue

            def report(_done: int, _total: int, _file: Path) -> None:
                nonlocal done
                done += 1
                if progress:
                    progress(done, total)

            items = [[Path(f) for f in json.loads(r["files"])] for r in rows]
            try:
                matches = await self._run(self._matcher(kind).match_all(items, report))
            except SearchStopped as exc:
                # The other kinds of this media type use the same service.
                stops.append(exc)
                stopped.add(search.media_type)
                continue
            for row, match in zip(rows, matches):
                await self._save_match(row["id"], kind, match)
        if stops:
            stops[0].others = stops[1:]
            raise stops[0]
        return total

    async def search_row(self, row_id: int, query: Optional[str] = None) -> None:
        """Search one row again, with the text typed or its own text.

        Raises:
            UnknownRow: No row has this id.
            SearchStopped: A key is missing or refused, or the quota is used.
        """
        row = self._row(row_id)
        kind = row["kind"]
        files = [Path(f) for f in json.loads(row["files"])]
        text = (query or "").strip() or None
        match = await self._run(self._matcher(kind).match(files, text))
        await self._save_match(row_id, kind, match)

    def _matcher(self, kind: str) -> BatchMatcher:
        search = SEARCHES[kind]
        return BatchMatcher(
            self._manager(search.media_type),
            search.content_type,
            search.parse,
            self._language if search.localized else None,
            search.same_work,
        )

    @staticmethod
    async def _run(awaitable: Any) -> Any:
        """Await a search; a key or quota problem stops it."""
        try:
            return await awaitable
        except APIAuthenticationError as exc:
            raise SearchStopped(KEY_REFUSED, service_id(exc.api_name)) from exc
        except APIRateLimitError as exc:
            raise SearchStopped(RATE_LIMITED, service_id(exc.api_name)) from exc

    async def _save_match(self, row_id: int, kind: str, match: BatchMatch) -> None:
        details = None
        if (
            kind == "episode"
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
        manager = self._manager(MediaType.VIDEO)
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
        if selected is not None and row["kind"] == "episode":
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
        names = self._new_names(row, files, candidates, selected, details)
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
        row: Any,
        files: List[str],
        candidates: List[Dict[str, Any]],
        selected: Optional[int],
        details: Optional[Dict[str, Any]],
    ) -> List[Optional[str]]:
        """The new path of each file under the destination, or None before a
        match.

        Movies and episodes get their file name; the other kinds the folders
        and the name the desktop batches give them (batch_target): the
        artist and album folder of a track, the author folder of a book, the
        platform folder of a game.
        """
        search = SEARCHES.get(row["kind"])
        if search is None or selected is None or not candidates:
            return [None] * len(files)
        candidate = dict(candidates[selected])
        if details:
            candidate["episodes"] = details["episodes"]
        item = create_media_item(
            candidate,
            search.factory_type,
            get_media_manager(),
            language=self._config.get("language", "en") or "en",
        )
        if item is None:
            return [None] * len(files)
        if row["media_type"] in ("movies", "tv"):
            return [
                self._video.generate_new_filename(item, Path(f).name) for f in files
            ]
        ops = self._batch_ops[row["media_type"]]
        alone = len(files) == 1
        names: List[Optional[str]] = []
        for file in files:
            folders, name = ops.batch_target(item, Path(file), alone)
            names.append("/".join([*folders, name]))
        return names


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


def search_error(exc: SearchStopped) -> Dict[str, Any]:
    """{"code", "service"}, and "others" when other services stopped too."""
    error: Dict[str, Any] = {"code": exc.code, "service": exc.service}
    if exc.others:
        error["others"] = [{"code": o.code, "service": o.service} for o in exc.others]
    return error
