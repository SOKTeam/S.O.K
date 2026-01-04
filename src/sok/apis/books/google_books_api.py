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
Google Books API implementation.

API Documentation: https://developers.google.com/books/docs/v1/using
Note: Google Books API is free but has rate limits.
"""

from typing import Dict, List, Any, Optional
from sok.apis.base_api import BaseAPI
from sok.core.interfaces import MediaType, ContentType


class GoogleBooksApi(BaseAPI):
    """Google Books API implementation for book search and metadata.

    Provides access to millions of books with detailed information
    including authors, ISBNs, publishers, and descriptions.

    Attributes:
        api_key: Google API key for authenticated requests.
        base_url: Base URL for the Google Books API.

    Note:
        Free API with daily quota limits.
    """

    def __init__(self, api_key: str = ""):
        """Initialize Google Books API.

        Args:
            api_key: Google Books API key (optional for basic usage).
        """
        super().__init__(api_key, "https://www.googleapis.com/books/v1/")

    @property
    def supported_media_types(self) -> List[MediaType]:
        """Return supported media types.

        Returns:
            List containing MediaType.BOOK.
        """
        return [MediaType.BOOK]

    @property
    def supported_content_types(self) -> List[ContentType]:
        """Return supported content types.

        Returns:
            List containing BOOK, EBOOK, and COMIC content types.
        """
        return [ContentType.BOOK, ContentType.EBOOK, ContentType.COMIC]

    async def get_related_items(self, item_id, content_type, **kwargs):
        """Get related items (not supported by Google Books).

        Args:
            item_id: Book identifier.
            content_type: Type of content.
            **kwargs: Additional parameters.

        Raises:
            NotImplementedError: Always raised as this API doesn't support related items.
        """
        raise NotImplementedError(
            "Google Books API does not support related items retrieval."
        )

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Search for books on Google Books.

        Args:
            query: Search query (title, author, ISBN, etc.).
            content_type: Content type to search for.
            **kwargs: Additional parameters (max_results, language, etc.).

        Returns:
            Dictionary with 'results' list of matching books.
        """
        params = {
            "q": query,
            "maxResults": kwargs.get("max_results", 10),
            "langRestrict": kwargs.get("language", "en"),
        }

        if self.api_key:
            params["key"] = self.api_key

        response = await self._make_request("volumes", params)

        results = []
        for item in response.get("items", []):
            volume_info = item.get("volumeInfo", {})
            results.append(
                {
                    "id": item.get("id"),
                    "title": volume_info.get("title"),
                    "author": ", ".join(volume_info.get("authors", [])),
                    "publisher": volume_info.get("publisher"),
                    "published_date": volume_info.get("publishedDate"),
                    "description": volume_info.get("description"),
                    "isbn": self._extract_isbn(
                        volume_info.get("industryIdentifiers", [])
                    ),
                    "page_count": volume_info.get("pageCount"),
                    "categories": volume_info.get("categories", []),
                    "language": volume_info.get("language"),
                }
            )

        return {"results": results}

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Get detailed book information.

        Args:
            item_id: Google Books volume ID.
            content_type: Content type of the book.
            **kwargs: Additional parameters.

        Returns:
            Dictionary with detailed book metadata.
        """
        params = {"key": self.api_key} if self.api_key else {}

        response = await self._make_request(f"volumes/{item_id}", params)
        volume_info = response.get("volumeInfo", {})

        return {
            "id": response.get("id"),
            "title": volume_info.get("title"),
            "author": ", ".join(volume_info.get("authors", [])),
            "publisher": volume_info.get("publisher"),
            "published_date": volume_info.get("publishedDate"),
            "description": volume_info.get("description"),
            "isbn": self._extract_isbn(volume_info.get("industryIdentifiers", [])),
            "isbn13": self._extract_isbn13(volume_info.get("industryIdentifiers", [])),
            "page_count": volume_info.get("pageCount"),
            "categories": volume_info.get("categories", []),
            "language": volume_info.get("language"),
            "image_url": volume_info.get("imageLinks", {}).get("thumbnail"),
        }

    def _extract_isbn(self, identifiers: List[Dict]) -> Optional[str]:
        """Extract ISBN-10 from identifiers.

        Args:
            identifiers: List of industry identifier dictionaries.

        Returns:
            ISBN-10 string if found, None otherwise.
        """
        for identifier in identifiers:
            if identifier.get("type") == "ISBN_10":
                return identifier.get("identifier")
        return None

    def _extract_isbn13(self, identifiers: List[Dict]) -> Optional[str]:
        """Extract ISBN-13 from identifiers.

        Args:
            identifiers: List of industry identifier dictionaries.

        Returns:
            ISBN-13 string if found, None otherwise.
        """
        for identifier in identifiers:
            if identifier.get("type") == "ISBN_13":
                return identifier.get("identifier")
        return None
