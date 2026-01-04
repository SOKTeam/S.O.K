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
Track class for individual music tracks.
"""

from typing import Optional, Dict, Any
from sok.media.base_media import BaseMedia
from sok.core.interfaces import MediaType, ContentType
from sok.core.media_manager import UniversalMediaManager
from sok.core.utils import format_name


class Track(BaseMedia):
    """Class for managing individual music tracks.

    Represents a single music track with metadata.

    Attributes:
        artist: Track artist name.
        album: Album name.
        album_id: Album ID.
        track_number: Track number in album.
        duration: Duration in seconds.
        isrc: International Standard Recording Code.
        explicit: Whether track contains explicit content.

    Example:
        >>> manager = UniversalMediaManager()
        >>> track = Track("Bohemian Rhapsody", "en", manager, artist="Queen")
        >>> await track.search_and_set_media()
        >>> print(track.get_formatted_name())
        01 - Bohemian Rhapsody
    """

    def __init__(
        self,
        name: str,
        language: str,
        media_manager: UniversalMediaManager,
        artist: str = "",
        album: str = "",
        track_number: int = 1,
    ):
        """Initialize a Track instance.

        Args:
            name: Track title.
            language: Language code.
            media_manager: The API manager.
            artist: Artist name.
            album: Album name.
            track_number: Track number in album.
        """
        super().__init__(
            name, MediaType.MUSIC, ContentType.TRACK, media_manager, language
        )
        self.artist = artist
        self.album = album
        self.album_id: Optional[str] = None
        self.track_number = track_number
        self.duration: Optional[int] = None
        self.isrc: Optional[str] = None
        self.explicit: bool = False

    def get_formatted_name(self) -> str:
        """Return the formatted track name.

        Format: '## - Track Title'

        Returns:
            Formatted track name.
        """
        track_num_str = f"{self.track_number:02d}"
        return f"{track_num_str} - {format_name(self.title)}"

    def get_full_name(self) -> str:
        """Return the full track name with artist.

        Returns:
            Full track name (e.g., 'Queen - Bohemian Rhapsody').
        """
        if self.artist:
            return f"{format_name(self.artist)} - {format_name(self.title)}"
        return format_name(self.title)

    def get_duration_formatted(self) -> str:
        """Return formatted duration (MM:SS).

        Returns:
            Formatted duration string.
        """
        if self.duration:
            minutes = self.duration // 60
            seconds = self.duration % 60
            return f"{minutes}:{seconds:02d}"
        return "0:00"

    async def get_details(self) -> None:
        """Retrieve detailed track information.

        Fills attributes: artist, album, duration, isrc, etc.
        """
        if not self.id:
            await self.search_and_set_media()

        if self.id:
            details = await self.media_manager.get_details(
                self.id, ContentType.TRACK, language=self.language
            )

            if details:
                self.title = details.get("title", self.title)
                self.artist = details.get("artist", self.artist)
                self.album = details.get("album", self.album)
                self.album_id = details.get("album_id")
                self.track_number = details.get("track_number", self.track_number)
                self.duration = details.get("duration")
                self.isrc = details.get("isrc")
                self.explicit = details.get("explicit", False)
                self.description = details.get("description", "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the track to a dictionary.

        Returns:
            Track data as dictionary.
        """
        data = super().to_dict()
        data.update(
            {
                "artist": self.artist,
                "album": self.album,
                "album_id": self.album_id,
                "track_number": self.track_number,
                "duration": self.duration,
                "duration_formatted": self.get_duration_formatted(),
                "isrc": self.isrc,
                "explicit": self.explicit,
            }
        )
        return data

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], media_manager: UniversalMediaManager
    ) -> "Track":
        """Create a Track instance from a dictionary.

        Args:
            data: Track data.
            media_manager: The API manager.

        Returns:
            Track instance.
        """
        track = cls(
            name=data.get("title", ""),
            language=data.get("language", "en"),
            media_manager=media_manager,
            artist=data.get("artist", ""),
            album=data.get("album", ""),
            track_number=data.get("track_number", 1),
        )

        track.id = data.get("id")
        track.album_id = data.get("album_id")
        track.duration = data.get("duration")
        track.isrc = data.get("isrc")
        track.explicit = data.get("explicit", False)
        track.description = data.get("description", "")

        return track
