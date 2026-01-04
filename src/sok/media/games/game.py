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
Game class for video games.
"""

from typing import Optional, Dict, Any, List
from sok.media.base_media import BaseMedia
from sok.core.interfaces import MediaType, ContentType
from sok.core.media_manager import UniversalMediaManager
from sok.core.utils import format_name


class Game(BaseMedia):
    """Class for managing video games.

    Represents a video game with metadata like platform, developer, release date, etc.

    Attributes:
        platforms: Gaming platforms (PC, PS5, Xbox, etc.).
        developer: Game developer.
        publisher: Game publisher.
        release_date: Release date.
        genres: Game genres.
        esrb_rating: ESRB content rating.
        metacritic_score: Metacritic score (0-100).

    Example:
        >>> manager = UniversalMediaManager()
        >>> game = Game("The Witcher 3: Wild Hunt", "en", manager)
        >>> await game.search_and_set_media()
        >>> print(game.get_formatted_name())
        The Witcher 3 Wild Hunt (2015) [PC]
    """

    def __init__(
        self,
        name: str,
        language: str,
        media_manager: UniversalMediaManager,
        platform: str = "PC",
    ):
        """Initialize a Game instance.

        Args:
            name: Game title.
            language: Language code.
            media_manager: The API manager.
            platform: Gaming platform.
        """
        super().__init__(
            name, MediaType.GAME, ContentType.GAME, media_manager, language
        )
        self.platforms: List[str] = [platform] if platform else []
        self.developer: Optional[str] = None
        self.publisher: Optional[str] = None
        self.release_date: Optional[str] = None
        self.genres: List[str] = []
        self.esrb_rating: Optional[str] = None
        self.metacritic_score: Optional[int] = None

    def get_formatted_name(self) -> str:
        """Return the formatted game name.

        Format: 'Game Title (Year) [Platform]'

        Returns:
            Formatted game name.
        """
        name = format_name(self.title)

        if self.release_date:
            year = self.release_date.split("-")[0]
            name += f" ({year})"

        if self.platforms:
            name += f" [{self.platforms[0]}]"

        return name

    def get_folder_structure(self) -> List[str]:
        """Return the recommended folder structure.

        Returns:
            List containing the game folder name.
        """
        return [self.get_formatted_name()]

    async def get_details(self) -> None:
        """Retrieve detailed game information.

        Fills attributes: developer, publisher, genres, ratings, etc.
        """
        if not self.id:
            await self.search_and_set_media()

        if self.id:
            details = await self.media_manager.get_details(
                self.id, ContentType.GAME, language=self.language
            )

            if details:
                self.title = details.get("name", self.title)
                self.platforms = details.get("platforms", self.platforms)
                self.developer = details.get("developer")
                self.publisher = details.get("publisher")
                self.release_date = details.get("release_date")
                self.genres = details.get("genres", [])
                self.esrb_rating = details.get("esrb_rating")
                self.metacritic_score = details.get("metacritic_score")
                self.description = details.get("description", "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the game to a dictionary.

        Returns:
            Game data as dictionary.
        """
        data = super().to_dict()
        data.update(
            {
                "platforms": self.platforms,
                "developer": self.developer,
                "publisher": self.publisher,
                "release_date": self.release_date,
                "genres": self.genres,
                "esrb_rating": self.esrb_rating,
                "metacritic_score": self.metacritic_score,
            }
        )
        return data

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], media_manager: UniversalMediaManager
    ) -> "Game":
        """Create a Game instance from a dictionary.

        Args:
            data: Game data.
            media_manager: The API manager.

        Returns:
            Game instance.
        """
        platforms = data.get("platforms", [])
        game = cls(
            name=data.get("title", ""),
            language=data.get("language", "en"),
            media_manager=media_manager,
            platform=platforms[0] if platforms else "PC",
        )

        game.id = data.get("id")
        game.platforms = platforms
        game.developer = data.get("developer")
        game.publisher = data.get("publisher")
        game.release_date = data.get("release_date")
        game.genres = data.get("genres", [])
        game.esrb_rating = data.get("esrb_rating")
        game.metacritic_score = data.get("metacritic_score")
        game.description = data.get("description", "")

        return game
