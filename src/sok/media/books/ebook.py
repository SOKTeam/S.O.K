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
Ebook class for digital/electronic books.
"""

from sok.media.books.book import Book


class Ebook(Book):
    """
    Class for managing ebooks (digital books).

    Extends Book class with ebook-specific attributes.

    Additional Attributes:
    ----------------------
        file_format (str): File format (epub, pdf, mobi, azw3, etc.)
        file_size (int): File size in bytes
        drm_protected (bool): Whether the ebook has DRM protection

    Example:
    --------
        >>> manager = UniversalMediaManager()
        >>> ebook = Ebook("The Hobbit", "en", manager, author="J.R.R. Tolkien")
        >>> ebook.file_format = "epub"
        >>> print(ebook.get_formatted_name())
        J.R.R. Tolkien - The Hobbit (1937).epub
    """

    def __init__(self, name: str, language: str, media_manager, author: str = ""):
        """Initialize an Ebook instance."""
        super().__init__(name, language, media_manager, author)
        self.file_format: str = "epub"
        self.file_size: int = 0
        self.drm_protected: bool = False

    def get_formatted_name(self) -> str:
        """Returns formatted ebook name with file extension."""
        base_name = super().get_formatted_name()
        if self.file_format:
            return f"{base_name}.{self.file_format}"
        return base_name
