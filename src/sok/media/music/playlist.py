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
Playlist class for music playlists.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sok.media.base_media import BaseMedia
from sok.core.interfaces import MediaType, ContentType
from sok.core.media_manager import UniversalMediaManager
from sok.core.utils import format_name


class Playlist(BaseMedia):
    """Class for managing music playlists.

    Represents a collection of tracks organized in a playlist.

    Attributes:
        owner: Playlist owner/creator.
        tracks: List of tracks in the playlist.
        track_count: Total number of tracks.
        duration_total: Total duration in seconds.
        is_public: Whether the playlist is public.
        created_at: Playlist creation date.
        updated_at: Last update date.

    Example:
        >>> manager = UniversalMediaManager()
        >>> playlist = Playlist("Summer Vibes", "en", manager, owner="John Doe")
        >>> playlist.add_track({"id": "123", "title": "Song 1", "artist": "Artist 1"})
        >>> print(playlist.get_formatted_name())
        Summer Vibes [15 tracks]
    """

    def __init__(
        self,
        name: str,
        language: str,
        media_manager: UniversalMediaManager,
        owner: str = "",
    ):
        """Initialize a Playlist instance.

        Args:
            name: Playlist name.
            language: Language code.
            media_manager: The API manager.
            owner: Playlist owner name.
        """
        super().__init__(
            name, MediaType.MUSIC, ContentType.PLAYLIST, media_manager, language
        )
        self.owner = owner
        self.tracks: List[Dict[str, Any]] = []
        self.track_count: int = 0
        self.duration_total: int = 0
        self.is_public: bool = True
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None

    def get_formatted_name(self) -> str:
        """Return the formatted playlist name.

        Returns:
            Formatted playlist name with track count.
        """
        if self.track_count > 0:
            return f"{format_name(self.title)} [{self.track_count} tracks]"
        return format_name(self.title)

    def add_track(self, track: Dict[str, Any]) -> None:
        """Add a track to the playlist.

        Args:
            track: Track data dictionary.
        """
        self.tracks.append(track)
        self.track_count = len(self.tracks)

        if "duration" in track:
            self.duration_total += track["duration"]

        self.updated_at = datetime.now()

    def remove_track(self, track_id: str) -> bool:
        """Remove a track from the playlist.

        Args:
            track_id: ID of the track to remove.

        Returns:
            True if track was removed, False otherwise.
        """
        for i, track in enumerate(self.tracks):
            if track.get("id") == track_id:
                removed_track = self.tracks.pop(i)
                self.track_count = len(self.tracks)

                if "duration" in removed_track:
                    self.duration_total -= removed_track["duration"]

                self.updated_at = datetime.now()
                return True
        return False

    def get_duration_formatted(self) -> str:
        """Return formatted total duration (HH:MM:SS).

        Returns:
            Formatted duration string.
        """
        if self.duration_total > 0:
            hours = self.duration_total // 3600
            minutes = (self.duration_total % 3600) // 60
            seconds = self.duration_total % 60

            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            return f"{minutes}:{seconds:02d}"
        return "0:00"

    async def get_details(self) -> None:
        """Retrieve detailed playlist information.

        Fills attributes: tracks, owner, dates, etc.
        """
        if not self.id:
            await self.search_and_set_media()

        if self.id:
            details = await self.media_manager.get_details(
                self.id, ContentType.PLAYLIST, language=self.language
            )

            if details:
                self.title = details.get("name", self.title)
                self.owner = details.get("owner", self.owner)
                self.tracks = details.get("tracks", [])
                self.track_count = len(self.tracks)
                self.duration_total = details.get("duration_total", 0)
                self.is_public = details.get("is_public", True)
                self.description = details.get("description", "")

                if "created_at" in details:
                    self.created_at = datetime.fromisoformat(details["created_at"])
                if "updated_at" in details:
                    self.updated_at = datetime.fromisoformat(details["updated_at"])

    def to_dict(self) -> Dict[str, Any]:
        """Convert the playlist to a dictionary.

        Returns:
            Playlist data as dictionary.
        """
        data = super().to_dict()
        data.update(
            {
                "owner": self.owner,
                "tracks": self.tracks,
                "track_count": self.track_count,
                "duration_total": self.duration_total,
                "duration_formatted": self.get_duration_formatted(),
                "is_public": self.is_public,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
        )
        return data

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], media_manager: UniversalMediaManager
    ) -> "Playlist":
        """Create a Playlist instance from a dictionary.

        Args:
            data: Playlist data.
            media_manager: The API manager.

        Returns:
            Playlist instance.
        """
        playlist = cls(
            name=data.get("title", ""),
            language=data.get("language", "en"),
            media_manager=media_manager,
            owner=data.get("owner", ""),
        )

        playlist.id = data.get("id")
        playlist.tracks = data.get("tracks", [])
        playlist.track_count = data.get("track_count", len(playlist.tracks))
        playlist.duration_total = data.get("duration_total", 0)
        playlist.is_public = data.get("is_public", True)
        playlist.description = data.get("description", "")

        if data.get("created_at"):
            playlist.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            playlist.updated_at = datetime.fromisoformat(data["updated_at"])

        return playlist
