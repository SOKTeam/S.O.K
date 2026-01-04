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
Book class for physical and digital books.
"""

from typing import Optional, Dict, Any, List
from sok.media.base_media import BaseMedia
from sok.core.interfaces import MediaType, ContentType
from sok.core.media_manager import UniversalMediaManager
from sok.core.utils import format_name


class Book(BaseMedia):
    """Class for managing books (physical and digital).

    Represents a book with metadata like author, ISBN, publisher, etc.

    Attributes:
        author: Book author(s).
        isbn: International Standard Book Number.
        isbn13: 13-digit ISBN.
        publisher: Publisher name.
        published_date: Publication date.
        page_count: Number of pages.
        language_code: Book language (ISO code).
        categories: Book categories/genres.

    Example:
        >>> manager = UniversalMediaManager()
        >>> book = Book("Harry Potter and the Philosopher's Stone", "en", manager)
        >>> await book.search_and_set_media()
        >>> print(book.get_formatted_name())
        J.K. Rowling - Harry Potter and the Philosopher's Stone (1997)
    """

    def __init__(
        self,
        name: str,
        language: str,
        media_manager: UniversalMediaManager,
        author: str = "",
    ):
        """Initialize a Book instance.

        Args:
            name: Book title.
            language: Language code.
            media_manager: The API manager.
            author: Author name.
        """
        super().__init__(
            name, MediaType.BOOK, ContentType.BOOK, media_manager, language
        )
        self.author = author
        self.isbn: Optional[str] = None
        self.isbn13: Optional[str] = None
        self.publisher: Optional[str] = None
        self.published_date: Optional[str] = None
        self.page_count: Optional[int] = None
        self.language_code: str = language
        self.categories: List[str] = []

    def get_formatted_name(self) -> str:
        """Return the formatted book name.

        Format: 'Author - Title (Year)'

        Returns:
            Formatted book name.
        """
        parts = []
        if self.author:
            parts.append(format_name(self.author))
        parts.append(format_name(self.title))

        name = " - ".join(parts)

        if self.published_date:
            year = self.published_date.split("-")[0]
            name += f" ({year})"

        return name

    def get_folder_structure(self) -> List[str]:
        """Return the recommended folder structure.

        Returns:
            List containing author and book folders.
        """
        folders = []
        if self.author:
            folders.append(format_name(self.author))
        folders.append(self.get_formatted_name())
        return folders

    async def get_details(self) -> None:
        """Retrieve detailed book information.

        Fills attributes: author, ISBN, publisher, pages, etc.
        """
        if not self.id:
            await self.search_and_set_media()

        if self.id:
            details = await self.media_manager.get_details(
                self.id, ContentType.BOOK, language=self.language
            )

            if details:
                self.title = details.get("title", self.title)
                self.author = details.get("author", self.author)
                self.isbn = details.get("isbn")
                self.isbn13 = details.get("isbn13")
                self.publisher = details.get("publisher")
                self.published_date = details.get("published_date")
                self.page_count = details.get("page_count")
                self.language_code = details.get("language", self.language_code)
                self.categories = details.get("categories", [])
                self.description = details.get("description", "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert the book to a dictionary.

        Returns:
            Book data as dictionary.
        """
        data = super().to_dict()
        data.update(
            {
                "author": self.author,
                "isbn": self.isbn,
                "isbn13": self.isbn13,
                "publisher": self.publisher,
                "published_date": self.published_date,
                "page_count": self.page_count,
                "language_code": self.language_code,
                "categories": self.categories,
            }
        )
        return data

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], media_manager: UniversalMediaManager
    ) -> "Book":
        """Create a Book instance from a dictionary.

        Args:
            data: Book data.
            media_manager: The API manager.

        Returns:
            Book instance.
        """
        book = cls(
            name=data.get("title", ""),
            language=data.get("language", "en"),
            media_manager=media_manager,
            author=data.get("author", ""),
        )

        book.id = data.get("id")
        book.isbn = data.get("isbn")
        book.isbn13 = data.get("isbn13")
        book.publisher = data.get("publisher")
        book.published_date = data.get("published_date")
        book.page_count = data.get("page_count")
        book.language_code = data.get("language_code", book.language)
        book.categories = data.get("categories", [])
        book.description = data.get("description", "")

        return book
