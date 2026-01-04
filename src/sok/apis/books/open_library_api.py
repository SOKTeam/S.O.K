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
Open Library API implementation.

API Documentation: https://openlibrary.org/developers/api
Note: Open Library API is free and requires no API key.
"""

from typing import Dict, List, Any
from sok.apis.base_api import BaseAPI
from sok.core.interfaces import MediaType, ContentType


class OpenLibraryApi(BaseAPI):
    """
    Open Library API implementation for book search and metadata.

    Free API providing access to millions of books without requiring an API key.
    """

    def __init__(self):
        """Initialize Open Library API (no API key required)."""
        super().__init__("", "https://openlibrary.org/")

    @property
    def supported_media_types(self) -> List[MediaType]:
        """Get supported media types.

        Returns:
            List containing BOOK media type.
        """
        return [MediaType.BOOK]

    @property
    def supported_content_types(self) -> List[ContentType]:
        """Get supported content types.

        Returns:
            List containing BOOK and EBOOK content types.
        """
        return [ContentType.BOOK, ContentType.EBOOK]

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Search for books on Open Library.

        Args:
            query: Search query string.
            content_type: Type of content to search for.
            **kwargs: Additional parameters (max_results).

        Returns:
            Dictionary containing search results.
        """
        params = {"q": query, "limit": kwargs.get("max_results", 10)}

        response = await self._make_request("search.json", params)

        results = []
        for doc in response.get("docs", []):
            results.append(
                {
                    "id": doc.get("key"),
                    "title": doc.get("title"),
                    "author": ", ".join(doc.get("author_name", [])),
                    "published_date": str(doc.get("first_publish_year")),
                    "isbn": doc.get("isbn", [None])[0] if doc.get("isbn") else None,
                }
            )

        return {"results": results}

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Get detailed book information from Open Library.

        Args:
            item_id: Open Library work key (e.g., '/works/OL123W').
            content_type: Type of content.
            **kwargs: Additional parameters.

        Returns:
            Dictionary containing book details.
        """
        response = await self._make_request(f"{item_id}.json")
        return {
            "id": item_id,
            "title": response.get("title"),
            "description": response.get("description", {}).get("value", ""),
        }

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """Get related items (not supported by Open Library).

        Args:
            item_id: Item identifier.
            content_type: Type of content.
            **kwargs: Additional parameters.

        Raises:
            NotImplementedError: Always raised as this API doesn't support related items.
        """
        raise NotImplementedError(
            "Open Library API does not support related items retrieval."
        )
