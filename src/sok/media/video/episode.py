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
Episode class for TV series episodes.
"""

from typing import Optional, Dict, Any
from sok.media.base_media import BaseMedia
from sok.core.interfaces import MediaType, ContentType
from sok.core.media_manager import UniversalMediaManager
from sok.core.utils import format_name


class Episode(BaseMedia):
    """Class for managing TV series episodes.

    Represents a single episode within a TV series season.

    Attributes:
        series_id: ID of the parent series.
        series_name: Name of the parent series.
        season_number: Season number.
        episode_number: Episode number within the season.
        air_date: Original air date.
        runtime: Duration in minutes.
        still_path: Path to episode still image.

    Example:
        >>> manager = UniversalMediaManager()
        >>> episode = Episode("Breaking Bad", "en", manager, season=1, episode=1)
        >>> await episode.search_and_set_media()
        >>> print(episode.get_formatted_name())
        Breaking Bad - S01E01 - Pilot
    """

    def __init__(
        self,
        series_name: str,
        language: str,
        media_manager: UniversalMediaManager,
        season_number: int = 1,
        episode_number: int = 1,
        series_id: Optional[str] = None,
    ):
        """Initialize an Episode instance.

        Args:
            series_name: Name of the parent TV series.
            language: Language code (e.g., 'en', 'fr').
            media_manager: The API manager.
            season_number: Season number (default: 1).
            episode_number: Episode number (default: 1).
            series_id: ID of the parent series if known.
        """
        super().__init__(
            series_name, MediaType.VIDEO, ContentType.EPISODE, media_manager, language
        )
        self.series_id = series_id
        self.series_name = series_name
        self.season_number = season_number
        self.episode_number = episode_number
        self.air_date: Optional[str] = None
        self.runtime: Optional[int] = None
        self.still_path: Optional[str] = None

    def get_formatted_name(self) -> str:
        """Return the formatted episode name.

        Format: 'Series Name - S##E## - Episode Title'

        Returns:
            Formatted episode name.
        """
        season_str = f"S{self.season_number:02d}"
        episode_str = f"E{self.episode_number:02d}"

        if self.title:
            return f"{format_name(self.series_name)} - {season_str}{episode_str} - {format_name(self.title)}"
        return f"{format_name(self.series_name)} - {season_str}{episode_str}"

    def get_episode_code(self) -> str:
        """Return the episode code.

        Returns:
            Episode code (e.g., 'S01E01').
        """
        return f"S{self.season_number:02d}E{self.episode_number:02d}"

    async def get_details(self) -> None:
        """Retrieve detailed episode information.

        Fills attributes: title, air_date, runtime, still_path, etc.
        """
        if not self.series_id:
            results = await self.media_manager.search(
                self.series_name, ContentType.TV_SERIES, language=self.language
            )
            items = results.get("results", [])
            if items:
                self.series_id = items[0].get("id")

        if self.series_id:
            get_details = getattr(self.media_manager, "get_episode_details", None)
            if get_details is not None:
                details = await get_details(
                    self.series_id,
                    self.season_number,
                    self.episode_number,
                    language=self.language,
                )

                if details:
                    self.id = details.get("id")
                    self.title = details.get("name", self.title)
                    self.description = details.get("overview", "")
                    self.air_date = details.get("air_date")
                    self.runtime = details.get("runtime")
                    self.still_path = details.get("still_path")
                    self.vote_average = details.get("vote_average")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the episode to a dictionary.

        Returns:
            Episode data as dictionary.
        """
        data = super().to_dict()
        data.update(
            {
                "series_id": self.series_id,
                "series_name": self.series_name,
                "season_number": self.season_number,
                "episode_number": self.episode_number,
                "air_date": self.air_date,
                "runtime": self.runtime,
                "still_path": self.still_path,
                "episode_code": self.get_episode_code(),
            }
        )
        return data

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], media_manager: UniversalMediaManager
    ) -> "Episode":
        """Create an Episode instance from a dictionary.

        Args:
            data: Episode data.
            media_manager: The API manager.

        Returns:
            Episode instance.
        """
        episode = cls(
            series_name=data.get("series_name", ""),
            language=data.get("language", "en"),
            media_manager=media_manager,
            season_number=data.get("season_number", 1),
            episode_number=data.get("episode_number", 1),
            series_id=data.get("series_id"),
        )

        episode.id = data.get("id")
        episode.title = data.get("title", "")
        episode.description = data.get("description", "")
        episode.air_date = data.get("air_date")
        episode.runtime = data.get("runtime")
        episode.still_path = data.get("still_path")
        episode.vote_average = data.get("vote_average")

        return episode
