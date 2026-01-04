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
"""Core interfaces and abstract base classes.

Defines the abstract interfaces for media APIs, media types, content types,
and media items that all implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum


class MediaType(Enum):
    """Supported media type categories.

    Attributes:
        VIDEO: Movies, TV series, documentaries.
        MUSIC: Albums, tracks, artists, playlists.
        BOOK: Books, ebooks, audiobooks, comics.
        GAME: Video games, DLCs.
    """

    VIDEO = "video"
    MUSIC = "music"
    BOOK = "book"
    GAME = "game"


class ContentType(Enum):
    """Specific content types within media categories.

    Used to specify the exact type of content when searching
    or retrieving details from media APIs.
    """

    MOVIE = "movie"
    TV_SERIES = "tv_series"
    EPISODE = "episode"
    DOCUMENTARY = "documentary"

    ALBUM = "album"
    TRACK = "track"
    ARTIST = "artist"
    PLAYLIST = "playlist"

    BOOK = "book"
    AUDIOBOOK = "audiobook"
    EBOOK = "ebook"
    COMIC = "comic"

    GAME = "game"
    DLC = "dlc"


class MediaAPI(ABC):
    """Abstract interface for all media APIs.

    Defines the contract that all API implementations must follow.
    Implementations should handle authentication, rate limiting,
    and response normalization internally.

    Example:
        >>> class MyAPI(MediaAPI):
        ...     @property
        ...     def supported_media_types(self) -> List[MediaType]:
        ...         return [MediaType.VIDEO]
    """

    @property
    @abstractmethod
    def supported_media_types(self) -> List[MediaType]:
        """Media types supported by this API.

        Returns:
            List of MediaType enum values this API can handle.
        """
        pass

    @property
    @abstractmethod
    def supported_content_types(self) -> List[ContentType]:
        """Content types supported by this API.

        Returns:
            List of ContentType enum values this API can handle.
        """
        pass

    @abstractmethod
    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Search for media items.

        Args:
            query: Search query string.
            content_type: Type of content to search for.
            **kwargs: Additional API-specific parameters.

        Returns:
            Dict with 'results' key containing list of matching items.
        """
        pass

    @abstractmethod
    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Retrieve detailed information about an item.

        Args:
            item_id: Unique identifier of the item.
            content_type: Type of content.
            **kwargs: Additional API-specific parameters.

        Returns:
            Dict containing detailed item information.
        """
        pass

    @abstractmethod
    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """Retrieve related items (episodes, tracks, chapters, etc.).

        Args:
            item_id: Unique identifier of the parent item.
            content_type: Type of content.
            **kwargs: Additional API-specific parameters.

        Returns:
            List of related item dictionaries.
        """
        pass


class MediaItem(ABC):
    """Abstract interface for all media items.

    Base class for all media domain objects (Movie, Series, Album, etc.).
    Provides common functionality for formatting names and generating
    folder structures.

    Attributes:
        title: The item's title/name.
        media_type: Category (VIDEO, MUSIC, etc.).
        content_type: Specific type (MOVIE, ALBUM, etc.).
        id: Unique identifier from the source API.
        metadata: Additional metadata dictionary.
    """

    def __init__(self, title: str, media_type: MediaType, content_type: ContentType):
        """Initialize a media item.

        Args:
            title: The item's display title.
            media_type: The media category.
            content_type: The specific content type.
        """
        self.title = title
        self.media_type = media_type
        self.content_type = content_type
        self.id: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    @abstractmethod
    def get_formatted_name(self) -> str:
        """Return the formatted name for the file.

        Returns:
            Formatted string suitable for use as a filename.
        """
        pass

    @abstractmethod
    def get_folder_structure(self) -> List[str]:
        """Return the recommended folder structure.

        Returns:
            List of folder names from root to item location.
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert the item to a dictionary.

        Returns:
            Dict representation of the media item.
        """
        return {
            "title": self.title,
            "media_type": self.media_type.value,
            "content_type": self.content_type.value,
            "id": self.id,
            "metadata": self.metadata,
        }


class FileOperations(ABC):
    """Interface for file operations specific to each media type.

    Implementations handle media-type-specific file operations like
    parsing filenames, generating new names, and validating extensions.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Supported file extensions for this media type.

        Returns:
            List of file extensions (e.g., ['.mp4', '.mkv']).
        """
        pass

    @abstractmethod
    def extract_info_from_filename(self, filename: str) -> Dict[str, Any]:
        """Extract information from a filename.

        Args:
            filename: The filename to parse.

        Returns:
            Dict containing extracted information (title, year, etc.).
        """
        pass

    @abstractmethod
    @abstractmethod
    def generate_new_filename(
        self, media_item: MediaItem, original_filename: str
    ) -> str:
        """Generate a new filename based on media item metadata.

        Args:
            media_item: The media item with metadata.
            original_filename: The original filename.

        Returns:
            New formatted filename.
        """
        pass
