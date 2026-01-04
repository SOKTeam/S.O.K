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
Search Worker for multi-API media lookup.
"""

from typing import List, Any
import logging
from PySide6.QtCore import Signal

from sok.ui.workers.base import BaseWorker
from sok.core.interfaces import ContentType, MediaType
from sok.core.media_manager import get_media_manager
from sok.core.exceptions import UnsupportedMediaTypeError, APINotFoundError, APIError

logger = logging.getLogger(__name__)


class SearchWorker(BaseWorker):
    """Worker for searching media across different APIs.

    Performs async media searches in a background thread.

    Signals:
        finished (list): Emitted with search results on completion.

    Attributes:
        TYPE_MAP: Content type string to enum mapping.
        MEDIA_TYPE_MAP: Media type string to enum mapping.
    """

    finished = Signal(list)

    TYPE_MAP = {
        "tv": ContentType.TV_SERIES,
        "movie": ContentType.MOVIE,
        "artist": ContentType.ARTIST,
        "album": ContentType.ALBUM,
        "book": ContentType.BOOK,
        "game": ContentType.GAME,
    }

    MEDIA_TYPE_MAP = {
        "tv": MediaType.VIDEO,
        "movie": MediaType.VIDEO,
        "artist": MediaType.MUSIC,
        "album": MediaType.MUSIC,
        "book": MediaType.BOOK,
        "game": MediaType.GAME,
    }

    def __init__(self, query: str, content_type: str = "tv", config=None):
        """Initialize the search worker.

        Args:
            query: Search query string.
            content_type: Type string (tv, movie, album, etc.).
            config: Configuration manager (uses default if None).
        """
        super().__init__(config)
        self._query = query
        self._type_str = content_type
        self._manager = get_media_manager()

    def execute(self):
        """Execute the search operation.

        Runs async search and emits results via finished signal.
        """
        if not self._loop:
            return
        results = self._loop.run_until_complete(self._search())
        self.finished.emit(results)

    async def _search(self) -> List[Any]:
        """Perform async media search.

        Returns:
            List of search results (max 10).

        Raises:
            RuntimeError: If no API is configured.
            APIError: If search request fails.
        """
        content_type = self.TYPE_MAP.get(self._type_str, ContentType.MOVIE)
        media_type = self.MEDIA_TYPE_MAP.get(self._type_str, MediaType.VIDEO)

        try:
            self._manager.get_current_api(media_type)
        except (UnsupportedMediaTypeError, APINotFoundError) as exc:
            logger.error("No API configured for %s", media_type.value, exc_info=exc)
            raise RuntimeError(f"No API configured for {media_type.value}.") from exc

        lang = self._config.get("language", "en")
        api_lang = f"{lang}-{lang.upper()}" if len(lang) == 2 else lang

        try:
            result = await self._manager.search(
                self._query, content_type, language=api_lang
            )
        except APIError as exc:
            logger.error(
                "Search failed for query '%s' (%s)",
                self._query,
                content_type.value,
                exc_info=exc,
            )
            raise

        if isinstance(result, dict):
            return result.get("results", [])[:10]
        return result[:10] if isinstance(result, list) else []
