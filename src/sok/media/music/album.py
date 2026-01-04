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
"""Album media class for music organization.

Provides the Album class for representing and organizing music albums
with track lists, artist info, and release metadata.
"""

from typing import List, Dict, Any, Optional
from sok.core.interfaces import MediaItem, MediaType, ContentType
from sok.core.utils import format_name


class Album(MediaItem):
    """Class for managing music albums.

    Represents a music album with tracks, artist info, and release metadata.

    Attributes:
        artist: Album artist or band name.
        year: Release year.
        tracks: List of track dictionaries with metadata.
        genre: Primary musical genre.
        label: Record label name.
    """

    def __init__(self, title: str, artist: str = "", year: Optional[int] = None):
        """Initialize an Album instance.

        Args:
            title: The album title.
            artist: Artist or band name (default: empty).
            year: Release year (default: None).
        """
        super().__init__(title, MediaType.MUSIC, ContentType.ALBUM)
        self.artist = artist
        self.year = year
        self.tracks: List[Dict[str, Any]] = []
        self.genre = ""
        self.label = ""

    def get_formatted_name(self) -> str:
        """Return the formatted album folder name.

        Returns:
            Formatted string like 'Artist - Album (Year)'.
        """
        if self.year:
            return format_name(f"{self.artist} - {self.title} ({self.year})")
        return format_name(f"{self.artist} - {self.title}")

    def get_folder_structure(self) -> List[str]:
        """Return the recommended folder hierarchy.

        Returns:
            List of folder names [artist, album].
        """
        folders = []
        if self.artist:
            folders.append(format_name(self.artist))
        folders.append(self.get_formatted_name())
        return folders

    def get_track_filename(self, track_number: int, track_title: str) -> str:
        """Generate the filename for a track.

        Args:
            track_number: The track's position on the album.
            track_title: The track's title.

        Returns:
            Formatted filename like '01 - Track Title'.
        """
        track_num_str = str(track_number).zfill(2)
        return format_name(f"{track_num_str} - {track_title}")
