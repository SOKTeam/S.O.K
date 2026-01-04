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
Artist class for music artists.
"""

from typing import Optional, Dict, Any, List
from sok.media.base_media import BaseMedia
from sok.core.interfaces import MediaType, ContentType
from sok.core.media_manager import UniversalMediaManager
from sok.core.utils import format_name


class Artist(BaseMedia):
    """Class for managing music artists.

    Represents a music artist or band with metadata and discography.

    Attributes:
        genres: List of musical genres.
        country: Artist's country of origin.
        formed_year: Year the artist/band was formed.
        biography: Artist biography.
        members: Band members (if applicable).
        albums: List of albums.
        top_tracks: List of popular tracks.

    Example:
        >>> manager = UniversalMediaManager()
        >>> artist = Artist("Queen", "en", manager)
        >>> await artist.search_and_set_media()
        >>> await artist.get_discography()
    """

    def __init__(self, name: str, language: str, media_manager: UniversalMediaManager):
        """Initialize an Artist instance.

        Args:
            name: Artist or band name.
            language: Language code.
            media_manager: The API manager.
        """
        super().__init__(
            name, MediaType.MUSIC, ContentType.ARTIST, media_manager, language
        )
        self.genres: List[str] = []
        self.country: Optional[str] = None
        self.formed_year: Optional[int] = None
        self.biography: str = ""
        self.members: List[str] = []
        self.albums: List[Dict[str, Any]] = []
        self.top_tracks: List[Dict[str, Any]] = []
        self.followers: Optional[int] = None

    def get_formatted_name(self) -> str:
        """Return the formatted artist name.

        Returns:
            Formatted artist name.
        """
        return format_name(self.title)

    def get_folder_structure(self) -> List[str]:
        """Return the recommended folder structure.

        Returns:
            List containing the artist folder name.
        """
        return [self.get_formatted_name()]

    async def get_details(self) -> None:
        """Retrieve detailed artist information.

        Fills attributes: genres, country, biography, members, etc.
        """
        if not self.id:
            await self.search_and_set_media()

        if self.id:
            details = await self.media_manager.get_details(
                self.id, ContentType.ARTIST, language=self.language
            )

            if details:
                self.title = details.get("name", self.title)
                self.genres = details.get("genres", [])
                self.country = details.get("country")
                self.formed_year = details.get("formed_year")
                self.biography = details.get("biography", "")
                self.members = details.get("members", [])
                self.followers = details.get("followers")
                self.description = self.biography

    async def get_discography(self) -> List[Dict[str, Any]]:
        """Retrieve artist's discography.

        Returns:
            List of albums.
        """
        if not self.id:
            await self.get_details()

        if self.id:
            get_albums = getattr(self.media_manager, "get_artist_albums", None)
            if get_albums is not None:
                albums = await get_albums(self.id, language=self.language)
                self.albums = albums
                return albums

        return []

    async def get_top_tracks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve artist's top tracks.

        Args:
            limit: Maximum number of tracks to retrieve.

        Returns:
            List of popular tracks.
        """
        if not self.id:
            await self.get_details()

        if self.id:
            get_tracks = getattr(self.media_manager, "get_artist_top_tracks", None)
            if get_tracks is not None:
                tracks = await get_tracks(self.id, limit=limit, language=self.language)
                self.top_tracks = tracks
                return tracks

        return []

    def to_dict(self) -> Dict[str, Any]:
        """Convert the artist to a dictionary.

        Returns:
            Artist data as dictionary.
        """
        data = super().to_dict()
        data.update(
            {
                "genres": self.genres,
                "country": self.country,
                "formed_year": self.formed_year,
                "biography": self.biography,
                "members": self.members,
                "followers": self.followers,
                "albums_count": len(self.albums),
                "top_tracks_count": len(self.top_tracks),
            }
        )
        return data

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], media_manager: UniversalMediaManager
    ) -> "Artist":
        """Create an Artist instance from a dictionary.

        Args:
            data: Artist data.
            media_manager: The API manager.

        Returns:
            Artist instance.
        """
        artist = cls(
            name=data.get("title", ""),
            language=data.get("language", "en"),
            media_manager=media_manager,
        )

        artist.id = data.get("id")
        artist.genres = data.get("genres", [])
        artist.country = data.get("country")
        artist.formed_year = data.get("formed_year")
        artist.biography = data.get("biography", "")
        artist.members = data.get("members", [])
        artist.followers = data.get("followers")
        artist.description = artist.biography

        return artist
