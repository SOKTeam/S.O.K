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
Audiobook class for audio book recordings.
"""

from typing import Optional
from sok.media.books.book import Book


class Audiobook(Book):
    """
    Class for managing audiobooks.

    Extends Book class with audiobook-specific attributes.

    Additional Attributes:
    ----------------------
        narrator (str): Audiobook narrator name
        duration (int): Total duration in seconds
        audio_format (str): Audio format (mp3, m4b, etc.)
        bitrate (int): Audio bitrate in kbps

    Example:
    --------
        >>> manager = UniversalMediaManager()
        >>> audiobook = Audiobook("1984", "en", manager, author="George Orwell")
        >>> audiobook.narrator = "Simon Prebble"
        >>> audiobook.duration = 36000
    """

    def __init__(self, name: str, language: str, media_manager, author: str = ""):
        """Initialize an Audiobook instance."""
        super().__init__(name, language, media_manager, author)
        self.narrator: Optional[str] = None
        self.duration: int = 0
        self.audio_format: str = "mp3"
        self.bitrate: int = 128

    def get_duration_formatted(self) -> str:
        """Returns formatted duration (HH:MM:SS)."""
        if self.duration > 0:
            hours = self.duration // 3600
            minutes = (self.duration % 3600) // 60
            seconds = self.duration % 60
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return "0:00:00"
