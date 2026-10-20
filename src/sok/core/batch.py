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
"""
Batch matching: find the online item of many files at once.

Each file (or group of files, such as the .cue and .bin of a game) gets a
search query read from its name, the candidates of the online database and
a status:

- Ready: one candidate has the title of the file and, when the file name
  gives a year, that year. It is selected and can be renamed as is.
- Pick one: candidates were found, but none or several match exactly. The
  most likely one is selected, and the user must confirm it.
- Missing: the search found nothing.

The module has no Qt dependency, so the desktop app and S.O.K Server share
it.
"""

import asyncio
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from sok.core.exceptions import APIError
from sok.core.interfaces import ContentType
from sok.file_operations.video_operations import VideoFileOperations

logger = logging.getLogger(__name__)

STATUS_READY = "ok"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_MISSING = "missing"

MAX_CANDIDATES = 5
SEARCH_CONCURRENCY = 4

# Keys of a search result that hold a title or a date, whatever the service.
TITLE_KEYS = ("title", "name", "original_title", "original_name")
DATE_KEYS = ("release_date", "first_air_date", "published_date", "year")

# Reads the search query and the year from the files of one item.
QueryParser = Callable[[Sequence[Path]], Tuple[str, Optional[int]]]


@dataclass
class BatchMatch:
    """Search result of one item of a batch.

    Attributes:
        files: The files of the item; one for a movie or a book.
        query: Search text, read from the file name or typed by the user.
        year: Year read from the file name, or None.
        candidates: Search results, best first as the service ranks them.
        selected: Index of the selected candidate, or None if there is none.
        status: STATUS_READY, STATUS_AMBIGUOUS or STATUS_MISSING.
    """

    files: List[Path]
    query: str
    year: Optional[int]
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    selected: Optional[int] = None
    status: str = STATUS_MISSING

    @property
    def file(self) -> Path:
        """The first file, which names the item."""
        return self.files[0]


def normalize_title(text: str) -> str:
    """Reduce a title to its letters and digits, for comparison.

    Accents, case, punctuation and spaces are ignored, and "&" counts as
    "and": "Dune: Part Two" and "dune.part.two" are the same title.
    """
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.casefold().replace("&", "and")
    return re.sub(r"[^0-9a-z]+", "", text)


def candidate_year(candidate: Dict[str, Any]) -> Optional[int]:
    """Year of a search result, from its first date field."""
    for key in DATE_KEYS:
        value = candidate.get(key)
        if value:
            match = re.match(r"\d{4}", str(value))
            if match:
                return int(match.group())
    return None


def title_matches(query: str, candidate: Dict[str, Any]) -> bool:
    """True if the candidate has the query as title or original title."""
    wanted = normalize_title(query)
    return bool(wanted) and any(
        normalize_title(str(candidate.get(key) or "")) == wanted for key in TITLE_KEYS
    )


def evaluate(
    query: str, year: Optional[int], candidates: List[Dict[str, Any]]
) -> Tuple[Optional[int], str]:
    """Choose the candidate to select and the status of an item.

    Args:
        query: Search text.
        year: Year read from the file name, or None.
        candidates: Search results.

    Returns:
        The index of the candidate to select (None without candidates) and
        the status.
    """
    if not candidates:
        return None, STATUS_MISSING

    titled = [i for i, c in enumerate(candidates) if title_matches(query, c)]
    if year is None:
        if len(titled) == 1:
            return titled[0], STATUS_READY
        return (titled[0] if titled else 0), STATUS_AMBIGUOUS

    exact = [i for i in titled if candidate_year(candidates[i]) == year]
    if len(exact) == 1:
        return exact[0], STATUS_READY
    if exact:
        return exact[0], STATUS_AMBIGUOUS
    # A translated title can differ from the file name: the year is then the
    # best hint.
    same_year = [i for i, c in enumerate(candidates) if candidate_year(c) == year]
    if same_year:
        return same_year[0], STATUS_AMBIGUOUS
    return (titled[0] if titled else 0), STATUS_AMBIGUOUS


def parse_movie(files: Sequence[Path]) -> Tuple[str, Optional[int]]:
    """Query and year of a movie file: "Dune.Part.Two.2024.mkv" → Dune Part Two."""
    info = VideoFileOperations().extract_info_from_filename(files[0].name)
    return info.get("title") or files[0].stem, info.get("year")


class BatchMatcher:
    """Search the online database for every item of a batch.

    Args:
        manager: The media manager (sok.core.media_manager).
        content_type: What to search, such as ContentType.MOVIE.
        parse: Reads the query and the year from the files of an item.
        language: Language of the results, such as "fr-FR", or None.
    """

    def __init__(
        self,
        manager: Any,
        content_type: ContentType,
        parse: QueryParser,
        language: Optional[str] = None,
    ) -> None:
        self._manager = manager
        self._content_type = content_type
        self._parse = parse
        self._language = language

    async def match(
        self, files: Sequence[Path], query: Optional[str] = None
    ) -> BatchMatch:
        """Search one item.

        Args:
            files: Files of the item.
            query: Search text typed by the user, instead of the file name.
                The year of the file name is kept.

        Returns:
            The match. A failed search gives no candidates (Missing).
        """
        parsed_query, year = self._parse(files)
        text = (query or parsed_query).strip()
        candidates: List[Dict[str, Any]] = []
        kwargs = {"language": self._language} if self._language else {}
        try:
            result = await self._manager.search(text, self._content_type, **kwargs)
            raw = result.get("results", []) if isinstance(result, dict) else result
            candidates = list(raw or [])[:MAX_CANDIDATES]
        except APIError as exc:
            logger.warning("Search failed for %s: %s", files[0].name, exc)
        selected, status = evaluate(text, year, candidates)
        return BatchMatch(list(files), text, year, candidates, selected, status)

    async def match_all(
        self,
        items: Sequence[Sequence[Path]],
        progress: Optional[Callable[[int, int, Path], None]] = None,
    ) -> List[BatchMatch]:
        """Search every item, a few at a time.

        Args:
            items: The files of each item.
            progress: Called with (done, total, first file) after each item.

        Returns:
            The matches, in the order of the items.
        """
        semaphore = asyncio.Semaphore(SEARCH_CONCURRENCY)
        total = len(items)
        done = 0

        async def run_one(files: Sequence[Path]) -> BatchMatch:
            nonlocal done
            async with semaphore:
                result = await self.match(files)
            done += 1
            if progress:
                progress(done, total, files[0])
            return result

        return list(await asyncio.gather(*(run_one(files) for files in items)))
