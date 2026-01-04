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
"""Media adapter registry and convenience functions.

Provides centralized access to content-type-specific adapters
for normalizing API responses.
"""

from typing import Any, Dict, List
from sok.core.interfaces import ContentType
from sok.core.adapters.media_adapters.base import Adapter
from sok.core.adapters.media_adapters.movie import MovieAdapter
from sok.core.adapters.media_adapters.tv import TvAdapter
from sok.core.adapters.media_adapters.music import MusicAdapter
from sok.core.adapters.media_adapters.book import BookAdapter
from sok.core.adapters.media_adapters.game import GameAdapter

_ADAPTERS: Dict[ContentType, Adapter] = {
    ContentType.MOVIE: MovieAdapter(),
    ContentType.DOCUMENTARY: MovieAdapter(),
    ContentType.TV_SERIES: TvAdapter(),
    ContentType.EPISODE: TvAdapter(),
    ContentType.ALBUM: MusicAdapter(),
    ContentType.TRACK: MusicAdapter(),
    ContentType.ARTIST: MusicAdapter(),
    ContentType.BOOK: BookAdapter(),
    ContentType.AUDIOBOOK: BookAdapter(),
    ContentType.EBOOK: BookAdapter(),
    ContentType.COMIC: BookAdapter(),
    ContentType.GAME: GameAdapter(),
    ContentType.DLC: GameAdapter(),
}


def _get_adapter(content_type: ContentType) -> Adapter:
    """Get the adapter for a content type.

    Args:
        content_type: The content type to get adapter for.

    Returns:
        Adapter instance for the content type.
    """
    return _ADAPTERS[content_type]


def adapt_search_results(
    content_type: ContentType, results: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Adapt search results using the appropriate adapter.

    Args:
        content_type: Type of content being searched.
        results: Raw API search results.

    Returns:
        Normalized search results dictionary.
    """
    return _get_adapter(content_type).adapt_search(content_type, results or [])


def adapt_details(content_type: ContentType, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt detail response using the appropriate adapter.

    Args:
        content_type: Type of content.
        payload: Raw API detail response.

    Returns:
        Normalized detail dictionary.
    """
    return _get_adapter(content_type).adapt_details(content_type, payload or {})


__all__ = [
    "adapt_search_results",
    "adapt_details",
    "Adapter",
    "MovieAdapter",
    "TvAdapter",
    "MusicAdapter",
    "BookAdapter",
    "GameAdapter",
]
