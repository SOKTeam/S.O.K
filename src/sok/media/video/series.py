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
"""TV Series media class for video organization.

Provides the Series class for searching, retrieving metadata, and
organizing TV series files with proper season/episode structure.
"""

from typing import Dict, List, Optional
from sok.media.base_media import BaseMedia
from sok.core.interfaces import MediaType, ContentType
from sok.core.media_manager import UniversalMediaManager
from sok.core.utils import format_name


class Series(BaseMedia):
    """Class for managing TV series.

    Provides functionality to search for series, retrieve season and
    episode information, and compute folder structures for organization.

    Attributes:
        seasons: Dictionary mapping season names to season numbers.
        episodes: Dictionary mapping episode codes to titles (e.g., {'S01E01': 'Pilot'}).

    Example:
        >>> manager = UniversalMediaManager()
        >>> series = Series("Breaking Bad", "en", manager)
        >>> await series.search_and_set_media()
        >>> await series.get_seasons()
    """

    def __init__(self, name: str, language: str, media_manager: UniversalMediaManager):
        """Initialize a Series instance.

        Args:
            name: The series name.
            language: Language code (e.g., 'fr', 'en').
            media_manager: The API manager instance.
        """
        super().__init__(
            name, MediaType.VIDEO, ContentType.TV_SERIES, media_manager, language
        )
        self.seasons: Dict[str, int] = {}
        self.episodes: Dict[str, str] = {}

    def get_formatted_name(self) -> str:
        """Return the formatted series name.

        Returns:
            Formatted series title.
        """
        return format_name(self.title)

    def get_folder_structure(self) -> List[str]:
        """Return the recommended folder structure for the series.

        Returns:
            List of folder names (e.g., ['Breaking Bad', 'Season 01']).
        """
        folders = [self.get_formatted_name()]
        for season_name in self.seasons.keys():
            folders.append(format_name(season_name))
        return folders

    async def get_seasons(self) -> None:
        """Retrieve information about the series seasons.

        Fills the seasons dictionary with available seasons.

        Raises:
            ValueError: If no ID found for the series.
        """
        if not self.id:
            await self.search_and_set_media()

        if not self.id:
            raise ValueError(f"No ID found for series '{self.title}'")

        details = await self.media_manager.get_details(
            self.id, ContentType.TV_SERIES, language=self.language
        )

        for season in details.get("seasons", []):
            self.seasons[season["name"]] = season["season_number"]

    async def get_episodes(self) -> None:
        """Retrieve information about all episodes of all seasons.

        Fills the episodes dictionary with format {'S01E01': 'Episode Title'}.
        """
        if not self.seasons:
            await self.get_seasons()

        api = self.media_manager.get_current_api(MediaType.VIDEO)
        get_episodes = getattr(api, "get_tv_episodes", None)
        if get_episodes is None:
            return

        for season_name, season_number in self.seasons.items():
            episodes = await get_episodes(self.id, season_number, self.language)

            for episode in episodes:
                season_str = str(episode["season_number"]).zfill(2)
                episode_str = str(episode["episode_number"]).zfill(2)
                episode_key = f"S{season_str}E{episode_str}"
                self.episodes[episode_key] = episode["name"]

    def get_episode_info(self, episode_code: str) -> Optional[str]:
        """Retrieve the episode title from its code.

        Args:
            episode_code: Episode code (e.g., 'S01E01').

        Returns:
            Episode title or None if not found.
        """
        return self.episodes.get(episode_code)

    def get_season_episodes(self, season_number: int) -> Dict[str, str]:
        """Retrieve all episodes of a specific season.

        Args:
            season_number: The season number.

        Returns:
            Dictionary mapping episode codes to titles for the season.
        """
        season_key = f"S{str(season_number).zfill(2)}"
        return {
            code: title
            for code, title in self.episodes.items()
            if code.startswith(season_key)
        }
