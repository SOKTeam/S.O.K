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
Comic class for comic books and graphic novels.
"""

from typing import Optional
from sok.media.books.book import Book


class Comic(Book):
    """
    Class for managing comics and graphic novels.

    Extends Book class with comic-specific attributes.

    Additional Attributes:
    ----------------------
        series (str): Comic series name
        issue_number (int): Issue number in series
        volume (int): Volume number
        artist (str): Comic artist/illustrator
        colorist (str): Colorist name

    Example:
    --------
        >>> manager = UniversalMediaManager()
        >>> comic = Comic("Batman: The Dark Knight Returns", "en", manager)
        >>> comic.issue_number = 1
        >>> comic.artist = "Frank Miller"
    """

    def __init__(self, name: str, language: str, media_manager, author: str = ""):
        """Initialize a Comic instance."""
        super().__init__(name, language, media_manager, author)
        self.series: Optional[str] = None
        self.issue_number: Optional[int] = None
        self.volume: Optional[int] = None
        self.artist: Optional[str] = None
        self.colorist: Optional[str] = None

    def get_formatted_name(self) -> str:
        """Returns formatted comic name with issue number."""
        if self.series and self.issue_number:
            return f"{self.series} #{self.issue_number:03d} - {self.title}"
        return super().get_formatted_name()
