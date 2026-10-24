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
Details Worker for fetching deep media metadata.
"""

import logging
from PySide6.QtCore import Signal
from sok.ui.workers.base import BaseWorker
from sok.core.interfaces import ContentType, MediaType
from sok.core.media_manager import get_media_manager
from sok.core.exceptions import APIError
from sok.core.series import fetch_episode_titles

logger = logging.getLogger(__name__)


class DetailsWorker(BaseWorker):
    """Worker for fetching detailed media metadata.

    Retrieves full metadata including episodes for series.

    Signals:
        finished (dict): Emitted with metadata dict on completion.

    Attributes:
        TYPE_MAP: Content type string to enum mapping.
    """

    finished = Signal(dict)

    TYPE_MAP = {
        "tv": ContentType.TV_SERIES,
        "movie": ContentType.MOVIE,
        "artist": ContentType.ARTIST,
        "album": ContentType.ALBUM,
        "book": ContentType.BOOK,
        "game": ContentType.GAME,
    }

    def __init__(
        self,
        media_id: str,
        content_type: str = "tv",
        fetch_episodes: bool = False,
        config=None,
    ):
        """Initialize the details worker.

        Args:
            media_id: API identifier for the media item.
            content_type: Type string (tv, movie, etc.).
            fetch_episodes: Whether to fetch episode list for series.
            config: Configuration manager (uses default if None).
        """
        super().__init__(config)
        self._media_id = media_id
        self._type_str = content_type
        self._fetch_episodes = fetch_episodes
        self._manager = get_media_manager()

    def execute(self):
        """Execute details fetch operation.

        Runs async fetch and emits result via finished signal.
        """
        if not self._loop:
            return
        details = self._loop.run_until_complete(self._get_details())
        self.finished.emit(details)

    async def _get_details(self) -> dict:
        """Fetch detailed media metadata.

        Returns:
            Metadata dictionary with optional episodes.

        Raises:
            APIError: If fetch request fails.
        """
        content_type = self.TYPE_MAP.get(self._type_str, ContentType.MOVIE)

        lang = self._config.get("language", "en")
        api_lang = f"{lang}-{lang.upper()}" if len(lang) == 2 else lang

        try:
            details = await self._manager.get_details(
                self._media_id, content_type, language=api_lang
            )
        except APIError as exc:
            logger.error(
                "Details fetch failed for %s (%s)",
                self._media_id,
                content_type.value,
                exc_info=exc,
            )
            raise

        if self._fetch_episodes and self._type_str == "tv":
            details["episodes"] = await self._fetch_all_episodes(details, api_lang)

        return details

    async def _fetch_all_episodes(self, details: dict, language: str) -> dict:
        """Fetch episode information for all seasons.

        Args:
            details: Series details containing season count.
            language: TMDB language code of the settings language, e.g. "en-EN",
                so episode titles match the language of the app.

        Returns:
            Dict mapping episode codes (S01E01) to titles.
        """
        return await fetch_episode_titles(
            self._manager.get_current_api(MediaType.VIDEO),
            self._media_id,
            details.get("number_of_seasons", 0),
            language,
        )
