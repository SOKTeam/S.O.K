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
"""Base media class with API integration.

Provides the BaseMedia class that extends MediaItem with functionality
to search for and retrieve metadata from configured media APIs.
"""

from abc import abstractmethod
from typing import List
from sok.core.interfaces import MediaItem, MediaType, ContentType
from sok.core.media_manager import UniversalMediaManager


class BaseMedia(MediaItem):
    """Base class for all media items with API integration.

    Extends MediaItem with functionality to search and retrieve
    metadata from configured media APIs.

    Attributes:
        media_manager: Manager for API operations.
        language: Language code for API requests.
        path: Storage path for the media item.
    """

    def __init__(
        self,
        title: str,
        media_type: MediaType,
        content_type: ContentType,
        media_manager: UniversalMediaManager,
        language: str = "en",
    ):
        """Initialize a media item with API support.

        Args:
            title: The item's display title.
            media_type: The media category (VIDEO, MUSIC, etc.).
            content_type: The specific content type.
            media_manager: Manager instance for API calls.
            language: Language code for searches (default: 'en').
        """
        super().__init__(title, media_type, content_type)
        self.media_manager = media_manager
        self.language = language
        self.path = "./"

    async def search_and_set_media(self) -> None:
        """Search for and populate media metadata from API.

        Searches using the configured API and updates this item's
        metadata with the first matching result.

        Raises:
            ValueError: If no results are found for the title.
        """
        results = await self.media_manager.search(
            self.title, self.content_type, language=self.language
        )

        if results.get("results"):
            first_result = results["results"][0]
            self.id = str(first_result.get("id"))

            if self.content_type in [ContentType.MOVIE, ContentType.DOCUMENTARY]:
                self.title = first_result.get(
                    "title", first_result.get("original_title", self.title)
                )
            elif self.content_type in [ContentType.TV_SERIES, ContentType.EPISODE]:
                self.title = first_result.get(
                    "name", first_result.get("original_name", self.title)
                )

            self.metadata = first_result
        else:
            raise ValueError(f"No results found for '{self.title}'")

    def set_path(self, path: str) -> None:
        """Set the storage path for this media item.

        Args:
            path: File system path where the media is stored.
        """
        self.path = path

    @abstractmethod
    def get_formatted_name(self) -> str:
        """Return the formatted filename for this media item.

        Returns:
            A formatted string suitable for use as a filename.
        """
        pass

    @abstractmethod
    def get_folder_structure(self) -> List[str]:
        """Return the recommended folder hierarchy for this item.

        Returns:
            A list of folder names representing the path structure.
        """
        pass
