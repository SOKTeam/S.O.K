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
"""What a TV series needs to be organized: its season folders and the
titles of its episodes.

The module has no Qt dependency, so the desktop app and S.O.K Server share
it.
"""

import logging
from typing import Any, Dict

from sok.core.exceptions import APIError

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
