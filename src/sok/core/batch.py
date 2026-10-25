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

- Ready: one candidate has the title of the file and, when the file
  gives them, its year, its author or artist, and its album. It is selected and can be renamed
  as is. Several candidates can count as one when they are the same work,
  such as the editions of a book. A track found only on compilations,
  live or remix releases is not Ready: its own album is still unknown.
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

from sok.core.exceptions import APIAuthenticationError, APIError, APIRateLimitError
from sok.core.interfaces import ContentType
from sok.file_operations.book_operations import BookFileOperations
from sok.file_operations.game_operations import GameFileOperations
from sok.file_operations.music_operations import MusicFileOperations
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


@dataclass
class ParsedName:
    """What the file name of an item tells about it.

    Attributes:
        query: Text to search.
        year: Year in the name, or None.
        title: Title to compare with the results; the query if None.
        author: Author (books) or artist (tracks), or None.
        album: Album of a track, from its tags, or None.
        search_kwargs: Extra search parameters, such as the title and the
            artist of a track for a precise search.
    """

    query: str
    year: Optional[int] = None
    title: Optional[str] = None
    author: Optional[str] = None
    album: Optional[str] = None
    search_kwargs: Dict[str, Any] = field(default_factory=dict)


# Reads the file name of an item.
QueryParser = Callable[[Sequence[Path]], ParsedName]
# True when two search results are the same work, such as two editions.
SameWork = Callable[[Dict[str, Any], Dict[str, Any]], bool]


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


def _raw_authors(candidate: Dict[str, Any]) -> List[str]:
    """Authors (books) or artist (music) of a search result, as written."""
    authors = (
        candidate.get("authors")
        or candidate.get("author")
        or candidate.get("artist")
        or []
    )
    if isinstance(authors, str):
        authors = [authors]
    return [str(a) for a in authors if a]


def candidate_authors(candidate: Dict[str, Any]) -> List[str]:
    """Authors (books) or artist (music) of a search result, normalized."""
    return [normalize_title(a) for a in _raw_authors(candidate)]


def _last_word(name: str) -> str:
    words = re.findall(r"[^\W_]+", name)
    return normalize_title(words[-1]) if words else ""


def author_matches(author: str, candidate: Dict[str, Any]) -> bool:
    """True if the author of the file name is an author of the result.

    "Herbert" and "F. Herbert" match "Frank Herbert": file names often give
    the last name. A full name must be the same: "Daft Punk" is not
    "Data Punk".
    """
    wanted = normalize_title(author)
    words = re.findall(r"[^\W_]+", author)
    # Only a last name, maybe after initials.
    last = _last_word(author) if all(len(w) == 1 for w in words[:-1]) else ""
    return bool(wanted) and any(
        normalize_title(a) == wanted or (last and _last_word(a) == last)
        for a in _raw_authors(candidate)
    )


def same_book(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Two results with the same title and authors are editions of one book."""
    return normalize_title(str(a.get("title") or "")) == normalize_title(
        str(b.get("title") or "")
    ) and set(candidate_authors(a)) == set(candidate_authors(b))


# Releases a track is on after its own album or single.
OTHER_RELEASES = ("compilation", "live", "remix")


def on_other_release(candidate: Dict[str, Any]) -> bool:
    """True for a track result on a compilation, a live or a remix release.

    The album the track came out on is then still unknown, so such a
    result is never Ready on its own.
    """
    return candidate.get("album_type") in OTHER_RELEASES


def same_album(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Two results with the same title and artist are one album, such as
    its explicit and clean versions."""
    return same_book(a, b)


def same_track(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Two results are the same track on the same album.

    A compilation, a live or a remix release does not count as another
    album: the track still came out on the first one.
    """
    return (
        normalize_title(str(a.get("title") or ""))
        == normalize_title(str(b.get("title") or ""))
        and set(candidate_authors(a)) == set(candidate_authors(b))
        and (
            normalize_title(str(a.get("album") or ""))
            == normalize_title(str(b.get("album") or ""))
            or on_other_release(b)
        )
    )


def _one_work(indexes: List[int], candidates, same_work: Optional[SameWork]) -> bool:
    """True if the candidates at these indexes are a single work."""
    if len(indexes) == 1:
        return True
    first = candidates[indexes[0]]
    return same_work is not None and all(
        same_work(first, candidates[i]) for i in indexes[1:]
    )


def _is_ready(indexes: List[int], candidates, same_work: Optional[SameWork]) -> bool:
    """True if the candidates at these indexes are one work, on its own release."""
    return (
        bool(indexes)
        and _one_work(indexes, candidates, same_work)
        and not on_other_release(candidates[indexes[0]])
    )


def evaluate(
    query: str,
    year: Optional[int],
    candidates: List[Dict[str, Any]],
    author: Optional[str] = None,
    same_work: Optional[SameWork] = None,
    album: Optional[str] = None,
) -> Tuple[Optional[int], str]:
    """Choose the candidate to select and the status of an item.

    Args:
        query: Title to compare with the results.
        year: Year read from the file name, or None.
        candidates: Search results.
        author: Author or artist read from the file, or None.
        same_work: Tells when several matching results are one work. By
            default every result is a different work (movies).
        album: Album of a track, from its tags: a result on that album is
            the one.

    Returns:
        The index of the candidate to select (None without candidates) and
        the status.
    """
    if not candidates:
        return None, STATUS_MISSING

    titled = [
        i
        for i, c in enumerate(candidates)
        if title_matches(query, c) and (not author or author_matches(author, c))
    ]
    # A track on its own album or single comes before its compilations.
    titled.sort(key=lambda i: on_other_release(candidates[i]))
    if album:
        on_album = [
            i
            for i in titled
            if normalize_title(str(candidates[i].get("album") or ""))
            == normalize_title(album)
        ]
        if on_album:
            return on_album[0], STATUS_READY

    # A year the results do not give (Deezer has none for albums) cannot
    # tell them apart: it is left out.
    if year is not None and not any(candidate_year(candidates[i]) for i in titled):
        year = None
    if year is None:
        if _is_ready(titled, candidates, same_work):
            return titled[0], STATUS_READY
        return (titled[0] if titled else 0), STATUS_AMBIGUOUS

    exact = [i for i in titled if candidate_year(candidates[i]) == year]
    if _is_ready(exact, candidates, same_work):
        return exact[0], STATUS_READY
    if exact:
        return exact[0], STATUS_AMBIGUOUS
    # A translated title can differ from the file name: the year is then the
    # best hint.
    same_year = [i for i, c in enumerate(candidates) if candidate_year(c) == year]
    if same_year:
        return same_year[0], STATUS_AMBIGUOUS
    return (titled[0] if titled else 0), STATUS_AMBIGUOUS


def parse_movie(files: Sequence[Path]) -> ParsedName:
    """Read a movie file name: "Dune.Part.Two.2024.mkv" → Dune Part Two, 2024."""
    info = VideoFileOperations().extract_info_from_filename(files[0].name)
    return ParsedName(info.get("title") or files[0].stem, info.get("year"))


def parse_series(files: Sequence[Path]) -> ParsedName:
    """Read the episodes of a series: "Severance.S01E02.mkv" → Severance.

    The title is the one the type detector gives the series (from the file
    name, or from the folders above a season folder), so the search and the
    group of the analysis agree. A year in the name ("Doctor.Who.2005.…") is
    the year of the first season.
    """
    from sok.file_operations.detection import MediaTypeDetector

    first = files[0]
    detected = MediaTypeDetector().detect_file(first)
    info = VideoFileOperations().extract_info_from_filename(first.name)
    title = (detected.title if detected else None) or info.get("title") or first.stem
    year = info.get("year")
    # "Doctor Who 2005", "Doctor Who (2005)": the year is not part of the title.
    match = _SERIES_YEAR.match(title)
    if match and not year:
        title, year = match.group(1), int(match.group(2))
    return ParsedName(title, year)


_SERIES_YEAR = re.compile(r"^(.*\S)[\s.]+\(?((?:19[3-9]|20[0-9])\d)\)?$")


# "Daft Punk - Discovery (2001)", "Daft Punk - 2001 - Discovery".
_ALBUM_FOLDER = re.compile(
    r"^(?P<artist>.+?)\s+-\s+(?:(?P<year1>\d{4})\s+-\s+)?(?P<album>.+?)"
    r"(?:\s*[(\[](?P<year2>\d{4})[)\]])?$"
)
# The tags of a release after the name: "[FLAC]", "{Vinyl}", "(320 kbps)",
# "[24bit-96kHz]". A year in brackets ("[1997]") is kept for _ALBUM_FOLDER.
_RELEASE_TAGS = re.compile(
    r"(?:\s*(?:[\[{](?!\d{4}[\]}])[^\[\]{}]*[\]}]"
    r"|\((?=[^()]*\b(?:flac|mp3|aac|alac|ogg|opus|wav|web|cd|vinyl|kbps|\d+\s*bit|\d+\s*khz)\b)"
    r"[^()]*\)))+$",
    re.IGNORECASE,
)


def _most_common(values: List[Any]) -> Any:
    """The value most files give, or None."""
    counts: Dict[Any, int] = {}
    for value in values:
        if value:
            counts[value] = counts.get(value, 0) + 1
    return max(counts, key=lambda v: counts[v]) if counts else None


def parse_album(files: Sequence[Path]) -> ParsedName:
    """Read the tracks of an album: its title, artist and year.

    The album and the artist most tracks give in their tags (the album
    artist first), then the name of the folder: "Daft Punk - Discovery
    (2001)". A year the results do not give is not compared (see
    evaluate).
    """
    ops = MusicFileOperations()
    tags = [ops.read_metadata(str(file)) for file in files]
    album = _most_common([t.get("album") for t in tags])
    artist = _most_common([t.get("album_artist") or t.get("artist") for t in tags])
    year = _most_common([t.get("year") for t in tags])
    if not album:
        from sok.file_operations.detection import DISC_FOLDER_PATTERN

        folder = files[0].parent
        if DISC_FOLDER_PATTERN.match(folder.name):
            folder = folder.parent
        name = _RELEASE_TAGS.sub("", folder.name).strip() or folder.name
        match = _ALBUM_FOLDER.match(name)
        if match:
            album = match.group("album").strip()
            artist = artist or match.group("artist").strip()
            found = match.group("year1") or match.group("year2")
            year = year or (int(found) if found else None)
        else:
            album = name
    query = f"{album} {artist}" if artist else album
    return ParsedName(query, year, album, artist)


def parse_book(files: Sequence[Path]) -> ParsedName:
    """Read a book file name: "Frank Herbert - Dune.epub" → Dune, by Herbert.

    The author is added to the search, which finds the right book more
    often, but only the title and the author are compared with the results.
    The year is left out: it is often the year of the first edition, while
    the results are later editions.
    """
    ops = BookFileOperations()
    info = ops.extract_info_from_filename(files[0].name)
    title = ops.clean_title(info.get("title") or files[0].stem)
    author = info.get("author")
    query = f"{title} {author}" if author else title
    return ParsedName(query, None, title, author)


def parse_game(files: Sequence[Path]) -> ParsedName:
    """Read a game file name: "Crash Bandicoot (USA) (Track 2).bin" → Crash Bandicoot.

    The region and the other tags are left out of the search.
    """
    info = GameFileOperations().extract_info_from_filename(files[0].name)
    return ParsedName(info.get("title") or files[0].stem)


def parse_track(files: Sequence[Path]) -> ParsedName:
    """Read a track: its tags first (artist, title, album), then its name.

    Tags are what players show and are usually right; file names of
    downloads are often "01 - Title.mp3" with no artist.
    """
    ops = MusicFileOperations()
    tags = ops.read_metadata(str(files[0]))
    info = ops.extract_info_from_filename(files[0].name)
    title = tags.get("title") or info.get("title") or files[0].stem
    artist = tags.get("artist") or info.get("artist")
    album = tags.get("album") or info.get("album")
    if not artist and " - " in title:
        # "Daft Punk - Get Lucky.mp3", the usual name of a single.
        artist, title = (part.strip() for part in title.split(" - ", 1))
    query = f"{title} {artist}" if artist else title
    search_kwargs = {"title": title, "artist": artist} if artist else {}
    return ParsedName(query, None, title, artist, album, search_kwargs)


# Files that list the other files of a game.
_INDEX_EXTENSIONS = {".cue", ".m3u", ".gdi"}
# "(Disc 2)", "(Track 03)": parts of one game.
_GAME_PART = re.compile(r"\s*\((?:disc|disk|cd|track)\s*\d+[^)]*\)", re.IGNORECASE)


def group_game_files(files: List[Path]) -> List[List[Path]]:
    """Put the files of one game together: a .cue and its .bin, the discs.

    Files of the same folder whose names only differ by their extension or
    a "(Disc N)" / "(Track N)" part are one game.
    """
    groups: Dict[Tuple[Path, str], List[Path]] = {}
    for file in files:
        key = (file.parent, _GAME_PART.sub("", file.stem).casefold().strip())
        groups.setdefault(key, []).append(file)
    # The file that lists the others (.cue, .m3u, .gdi) names the row.
    return [
        sorted(group, key=lambda f: f.suffix.lower() not in _INDEX_EXTENSIONS)
        for group in groups.values()
    ]


class BatchMatcher:
    """Search the online database for every item of a batch.

    Args:
        manager: The media manager (sok.core.media_manager).
        content_type: What to search, such as ContentType.MOVIE.
        parse: Reads the file name of an item.
        language: Language of the results, such as "fr-FR", or None.
        same_work: Tells when several results are one work (see evaluate).
    """

    def __init__(
        self,
        manager: Any,
        content_type: ContentType,
        parse: QueryParser,
        language: Optional[str] = None,
        same_work: Optional[SameWork] = None,
    ) -> None:
        self._manager = manager
        self._content_type = content_type
        self._parse = parse
        self._language = language
        self._same_work = same_work

    async def match(
        self, files: Sequence[Path], query: Optional[str] = None
    ) -> BatchMatch:
        """Search one item.

        Args:
            files: Files of the item.
            query: Search text typed by the user, instead of the file name.
                It is then also the title compared with the results; the
                year of the file name is kept.

        Returns:
            The match. A failed search gives no candidates (Missing).

        Raises:
            APIAuthenticationError: The key of the service is missing or wrong.
            APIRateLimitError: The quota of the service is used.
        """
        parsed = self._parse(files)
        text = (query or parsed.query).strip()
        title = text if query else (parsed.title or parsed.query)
        author = None if query else parsed.author
        album = None if query else parsed.album
        candidates: List[Dict[str, Any]] = []
        kwargs: Dict[str, Any] = {} if query else dict(parsed.search_kwargs)
        if self._language:
            kwargs["language"] = self._language
        try:
            result = await self._manager.search(text, self._content_type, **kwargs)
            raw = result.get("results", []) if isinstance(result, dict) else result
            candidates = list(raw or [])[:MAX_CANDIDATES]
        except (APIAuthenticationError, APIRateLimitError):
            # Every other item would fail the same way: stop the batch and
            # let the user know (missing key, quota used).
            raise
        except APIError as exc:
            logger.warning("Search failed for %s: %s", files[0].name, exc)
        selected, status = evaluate(
            title, parsed.year, candidates, author, self._same_work, album
        )
        return BatchMatch(list(files), text, parsed.year, candidates, selected, status)

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
