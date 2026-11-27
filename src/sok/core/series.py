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
"""What a TV series needs to be organized: its season folders, the titles
of its episodes, and the folder it already has in the library.

The module has no Qt dependency, so the desktop app and S.O.K Server share
it.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from sok.core.batch import candidate_year, normalize_title
from sok.core.exceptions import APIError
from sok.core.utils import is_video_file

logger = logging.getLogger(__name__)


def season_folders(details: Dict[str, Any], season_word: str) -> Dict[str, int]:
    """The folder name of each season, from the details of the series.

    "Season 2", or "Season 2 - The Name" when the season has a name of its
    own ("Season 2" or "Saison 2" in the details is no name).

    Args:
        details: Details of the series, with number_of_seasons and seasons.
        season_word: "Season" in the language of the interface.

    Returns:
        Folder name → season number, for seasons 1 to number_of_seasons.
    """
    names: Dict[Any, str] = {}
    for season in details.get("seasons", []):
        # The first entry of a season number counts.
        names.setdefault(season.get("season_number"), season.get("name") or "")
    folders: Dict[str, int] = {}
    for number in range(1, (details.get("number_of_seasons") or 0) + 1):
        name = names.get(number) or ""
        if name and name.lower() not in (f"season {number}", f"saison {number}"):
            folders[f"{season_word} {number} - {name}"] = number
        else:
            folders[f"{season_word} {number}"] = number
    return folders


async def fetch_episode_titles(
    api: Any, series_id: str, number_of_seasons: int, language: str
) -> Dict[str, str]:
    """The title of every episode of a series, season by season.

    A season that fails is left out (and logged): the episodes of the others
    still get their titles.

    Args:
        api: The video API of the series; it needs get_tv_episodes (TMDB).
        series_id: The id of the series in that API.
        number_of_seasons: From the details of the series.
        language: Language of the titles, such as "fr-FR".

    Returns:
        Episode code ("S01E01") → title; empty if the API has no episodes.
    """
    episodes: Dict[str, str] = {}
    if not hasattr(api, "get_tv_episodes"):
        logger.warning("API %s does not support get_tv_episodes", type(api).__name__)
        return episodes

    for season_number in range(1, number_of_seasons + 1):
        try:
            season_episodes = await api.get_tv_episodes(
                series_id, season_number, language
            )
        except (APIError, ValueError, KeyError, TypeError) as exc:
            logger.warning(
                "Episode fetch failed for %s season %s",
                series_id,
                season_number,
                exc_info=exc,
            )
            continue
        for episode in season_episodes:
            season = str(episode.get("season_number", season_number)).zfill(2)
            number = str(episode.get("episode_number", 0)).zfill(2)
            episodes[f"S{season}E{number}"] = episode.get("name", "")
    return episodes


# ------------------------------------------------------------ Existing folder

# How a folder was recognized (FolderMatch.how), from the surest.
BY_ID = "id"
BY_HISTORY = "history"
BY_TITLE = "title"

# The services whose ids a folder name or a tvshow.nfo can carry.
ID_SERVICES = ("tmdb", "tvdb", "imdb")

# "[tvdbid-81189]", "{tmdb-1396}", "(imdb tt0903747)", "[tvdb=81189]".
_ID_TAG = re.compile(
    r"[\[{(]\s*(tmdb|tvdb|imdb)(?:id)?\s*[-=: ]\s*([a-z0-9]+)\s*[\]})]",
    re.IGNORECASE,
)
# Tags in brackets and a year at the end, left out of the name compared.
_TAGS = re.compile(r"[\[{][^\]}]*[\]}]")
_YEAR = re.compile(r"[\s.(_-]*((?:19|20)\d{2})\)?\s*$")
# <tmdbid>1396</tmdbid>, <uniqueid type="tvdb">81189</uniqueid>, <imdb_id>.
_NFO_ID = re.compile(r"<(tmdb|tvdb|imdb)(?:_?id)?>\s*([a-z0-9]+)\s*<", re.IGNORECASE)
_NFO_UNIQUE = re.compile(
    r"<uniqueid[^>]*type=[\"']?(tmdb|tvdb|imdb)[\"']?[^>]*>\s*([a-z0-9]+)\s*<",
    re.IGNORECASE,
)
_SEASON = re.compile(
    r"^(?:season|saison|staffel|temporada|stagione|s)\s*0*(\d+)\b", re.I
)


@dataclass
class SeriesIdentity:
    """What tells a series apart, to find its folder.

    Attributes:
        title: The title of the series, as S.O.K names its folder.
        year: The year of its first episode, if known.
        titles: Every name of the series: title, original, translated.
        ids: Service → id ("tmdb", "tvdb", "imdb"), as text.
    """

    title: str
    year: Optional[int] = None
    titles: List[str] = field(default_factory=list)
    ids: Dict[str, str] = field(default_factory=dict)


@dataclass
class FolderMatch:
    """A folder of the library that holds the series.

    Attributes:
        path: The folder.
        root: Index of the destination folder that holds it.
        how: BY_ID, BY_HISTORY or BY_TITLE.
        source: The service of the id (BY_ID), or "nfo" when a tvshow.nfo
            gave it: "tvdb", "nfo".
        title: The title the name matched (BY_TITLE).
        seasons: The seasons it already has, from its season folders.
        episodes: The video files it already has.
    """

    path: str
    root: int
    how: str
    source: Optional[str] = None
    title: Optional[str] = None
    seasons: List[int] = field(default_factory=list)
    episodes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "root": self.root,
            "how": self.how,
            "source": self.source,
            "title": self.title,
            "seasons": self.seasons,
            "episodes": self.episodes,
        }


def series_identity(
    candidate: Dict[str, Any], details: Optional[Dict[str, Any]], service: str
) -> SeriesIdentity:
    """The identity of a series, from its search result and its details.

    Args:
        candidate: The search result picked.
        details: Its details; TMDB ones may carry alternative_titles and
            external_ids, TVDB ones aliases and remote_ids.
        service: The service of the candidate's id: "tmdb" or "tvdb".
    """
    details = details or {}
    title = candidate.get("name") or candidate.get("title") or ""
    titles = [
        title,
        candidate.get("original_name") or candidate.get("original_title") or "",
        details.get("name") or "",
        details.get("original_name") or "",
    ]
    alternative = details.get("alternative_titles") or {}
    titles += [t.get("title") or "" for t in alternative.get("results", [])]
    titles += [a for a in details.get("aliases", []) if isinstance(a, str)]
    ids: Dict[str, str] = {}
    if candidate.get("id") is not None:
        ids[service] = str(candidate["id"])
    external = details.get("external_ids") or {}
    for other in ID_SERVICES:
        value = external.get(f"{other}_id") or (details.get("remote_ids") or {}).get(
            other
        )
        if value and other not in ids:
            ids[other] = str(value)
    unique: List[str] = []
    for name in titles:
        if name and name not in unique:
            unique.append(name)
    return SeriesIdentity(title, candidate_year(candidate), unique, ids)


def folder_name_parts(name: str) -> tuple:
    """(name to compare, year, ids) of a folder name.

    "Breaking Bad (2008) [tvdbid-81189]" → ("breakingbad", 2008,
    {"tvdb": "81189"}).
    """
    ids = {m.group(1).lower(): m.group(2).lower() for m in _ID_TAG.finditer(name)}
    rest = _ID_TAG.sub(" ", name)
    rest = _TAGS.sub(" ", rest).strip()
    year = None
    match = _YEAR.search(rest)
    # A name that is only a year ("1923") stays a name.
    if match and match.start() > 0:
        year = int(match.group(1))
        rest = rest[: match.start()]
    return normalize_title(rest), year, ids


def nfo_ids(folder: str) -> Dict[str, str]:
    """The ids of the tvshow.nfo of a folder (Kodi, Jellyfin, Emby)."""
    path = os.path.join(folder, "tvshow.nfo")
    try:
        with open(path, encoding="utf-8", errors="replace") as nfo:
            text = nfo.read(200_000)
    except OSError:
        return {}
    ids: Dict[str, str] = {}
    for pattern in (_NFO_UNIQUE, _NFO_ID):
        for match in pattern.finditer(text):
            ids.setdefault(match.group(1).lower(), match.group(2).lower())
    return ids


def folder_content(folder: str) -> tuple:
    """(seasons, episodes) a series folder already has."""
    seasons = set()
    episodes = 0
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return [], 0
    for entry in entries:
        if entry.is_dir():
            match = _SEASON.match(entry.name)
            if match:
                seasons.add(int(match.group(1)))
            for _root, _dirs, files in os.walk(entry.path):
                episodes += sum(1 for f in files if is_video_file(f))
        elif is_video_file(entry.name):
            episodes += 1
    return sorted(seasons), episodes


def _same_id(ours: Dict[str, str], theirs: Dict[str, str]) -> Optional[bool]:
    """True when an id is the same, False when one differs, None when no
    service is shared."""
    shared = [s for s in theirs if s in ours]
    if not shared:
        return None
    return any(ours[s].lower() == theirs[s] for s in shared)


def find_series_folders(
    identity: SeriesIdentity,
    roots: List[str],
    known: Iterable[str] = (),
) -> List[FolderMatch]:
    """The folders of the library that already hold a series.

    The folders right under each root are compared, the surest way first:
    an id in the folder name or in its tvshow.nfo, then a folder S.O.K put
    the series in before (known), then the name (case, accents,
    punctuation, the year and the tags left out) against every title of
    the series. A folder whose id is another series is never taken, and a
    folder whose year is far from the series' is not taken by its name.
    Only the matches of the surest way found are returned.

    Args:
        identity: The series.
        roots: The destination folders of the series, in order.
        known: Folders where S.O.K put this series before.

    Returns:
        The matches, in the order of the roots then of the names; empty
        when the series has no folder yet.
    """
    titles = {normalize_title(t): t for t in identity.titles if normalize_title(t)}
    known_paths = {os.path.normcase(os.path.normpath(p)) for p in known}
    found: Dict[str, List[FolderMatch]] = {BY_ID: [], BY_HISTORY: [], BY_TITLE: []}
    for index, root in enumerate(roots):
        try:
            entries = sorted(
                (e for e in os.scandir(root) if e.is_dir()), key=lambda e: e.name
            )
        except OSError:
            continue
        for entry in entries:
            name, year, ids = folder_name_parts(entry.name)
            source: Optional[str] = None
            same = _same_id(identity.ids, ids)
            if same:
                source = next(s for s in ids if s in identity.ids)
            elif same is None:
                from_nfo = nfo_ids(entry.path)
                same = _same_id(identity.ids, from_nfo)
                if same:
                    source = "nfo"
            if same is False:
                # Another series, whatever its name.
                continue
            if same:
                found[BY_ID].append(FolderMatch(entry.path, index, BY_ID, source))
            elif os.path.normcase(os.path.normpath(entry.path)) in known_paths:
                found[BY_HISTORY].append(FolderMatch(entry.path, index, BY_HISTORY))
            elif name in titles and (
                year is None or identity.year is None or abs(year - identity.year) <= 1
            ):
                found[BY_TITLE].append(
                    FolderMatch(entry.path, index, BY_TITLE, title=titles[name])
                )
    for how in (BY_ID, BY_HISTORY, BY_TITLE):
        if found[how]:
            for match in found[how]:
                match.seasons, match.episodes = folder_content(match.path)
            return found[how]
    return []
