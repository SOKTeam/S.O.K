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
"""Movie media class for video organization.

Provides the Movie class for searching, retrieving metadata, and
organizing movie files with proper naming conventions.
"""

from typing import List, Optional
from sok.media.base_media import BaseMedia
from sok.core.interfaces import MediaType, ContentType
from sok.core.media_manager import UniversalMediaManager
from sok.core.utils import format_name


class Movie(BaseMedia):
    """Class for managing movies.

    Provides functionality to search for movies, retrieve detailed
    information, and compute formatted names for file organization.

    Attributes:
        year: Movie release year.
        director: Movie director name.
        runtime: Duration in minutes.
        genres: List of genre names.

    Example:
        >>> manager = UniversalMediaManager()
        >>> movie = Movie("Inception", "en", manager)
        >>> await movie.search_and_set_media()
    """

    def __init__(self, name: str, language: str, media_manager: UniversalMediaManager):
        """Initialize a Movie instance.

        Args:
            name: The movie name.
            language: Language code (e.g., 'fr', 'en').
            media_manager: The API manager instance.
        """
        super().__init__(
            name, MediaType.VIDEO, ContentType.MOVIE, media_manager, language
        )
        self.year: Optional[int] = None
        self.director: Optional[str] = None
        self.runtime: Optional[int] = None
        self.genres: List[str] = []

    def get_formatted_name(self) -> str:
        """Return the formatted movie name with the year.

        Returns:
            Formatted name (e.g., 'Inception (2010)').
        """
        if self.year:
            return format_name(f"{self.title} ({self.year})")
        return format_name(self.title)

    def get_folder_structure(self) -> List[str]:
        """Return the recommended folder structure for the movie.

        Returns:
            List containing the movie folder name.
        """
        return [self.get_formatted_name()]

    async def get_details(self) -> None:
        """Retrieve detailed movie information.

        Fills the attributes: year, director, runtime, genres, etc.

        Raises:
            ValueError: If no ID found for the movie.
        """
        if not self.id:
            await self.search_and_set_media()

        if not self.id:
            raise ValueError(f"No ID found for movie '{self.title}'")

        details = await self.media_manager.get_details(
            self.id, ContentType.MOVIE, language=self.language
        )

        release_date = details.get("release_date", "")
        if release_date:
            self.year = int(release_date.split("-")[0])

        self.runtime = details.get("runtime")
        self.genres = [genre["name"] for genre in details.get("genres", [])]

        self.metadata.update(details)
