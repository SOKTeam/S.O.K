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
TVDB API Implementation
The TVDB (TheTVDB.com) is a community database for TV series.

Documentation: https://thetvdb.github.io/v4-api/
"""

import aiohttp
import logging
from typing import Dict, List, Any, Optional
from sok.apis.base_api import BaseAPI
from sok.core.exceptions import APIError
from sok.core.interfaces import MediaType, ContentType

logger = logging.getLogger(__name__)


class TVDBApi(BaseAPI):
    """TVDB API v4 implementation.

    TVDB focuses primarily on TV series and provides detailed
    community data for television shows.

    Attributes:
        token: Bearer token for authenticated requests.

    Note:
        TVDB requires token authentication.
    """

    def __init__(self, api_key: str, token: Optional[str] = None):
        """Initialize TVDB API.

        Args:
            api_key: TVDB API key.
            token: Bearer token from previous session (if already connected).
        """
        super().__init__(api_key, "https://api4.thetvdb.com/v4/")
        self.token: Optional[str] = token

    @property
    def supported_media_types(self) -> List[MediaType]:
        """Return media types supported by TVDB.

        Returns:
            List containing MediaType.VIDEO.
        """
        return [MediaType.VIDEO]

    @property
    def supported_content_types(self) -> List[ContentType]:
        """Return content types supported by TVDB.

        Returns:
            List containing TV_SERIES and EPISODE content types.
        """
        return [ContentType.TV_SERIES, ContentType.EPISODE]

    async def _get_token(self) -> str:
        """Get TVDB authentication token.

        Returns:
            Authentication token string.
        """
        if self.token:
            return self.token

        auth_data = {"apikey": self.api_key}

        if not self.session:
            self.session = aiohttp.ClientSession()

        session = self.session
        assert session is not None

        async with session.post(
            f"{self.base_url}login",
            json=auth_data,
            headers={"Content-Type": "application/json"},
        ) as response:
            data = await response.json()
            self.token = data.get("data", {}).get("token", "")
            return self.token

    async def _make_authenticated_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to TVDB API.

        Args:
            endpoint: API endpoint
            params: Request parameters

        Returns:
            JSON API response
        """
        if not self.token:
            await self._get_token()

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

        return await self._make_request(endpoint, params, headers)

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """
        Search on TVDB.

        Args:
            query: Search term
            content_type: Content type
            **kwargs: Additional arguments (language, year, etc.)

        Returns:
            Search results in standardized format
        """
        if content_type == ContentType.TV_SERIES:
            return await self.search_series(query, **kwargs)
        elif content_type == ContentType.MOVIE:
            return await self.search_movies(query, **kwargs)
        else:
            raise ValueError(f"Content type not supported by TVDB: {content_type}")

    async def search_series(
        self, query: str, language: str = "eng", **kwargs
    ) -> Dict[str, Any]:
        """
        Search for TV series on TVDB.

        Args:
            query: Series name
            language: Language code (e.g., "eng", "fra")

        Returns:
            Search results
        """
        params = {"query": query, "type": "series"}

        if kwargs.get("year"):
            params["year"] = kwargs["year"]

        try:
            data = await self._make_authenticated_request("search", params)

            results = []
            for item in data.get("data", []):
                results.append(
                    {
                        "id": item.get("tvdb_id"),
                        "name": item.get("name"),
                        "original_name": item.get("name"),
                        "overview": item.get("overview", ""),
                        "first_air_date": item.get("first_air_date", ""),
                        "poster_path": item.get("image_url", ""),
                        "media_type": "tv",
                    }
                )

            return {"results": results}

        except (aiohttp.ClientError, APIError, KeyError, ValueError) as exc:
            logger.exception("TVDB search series failed", exc_info=exc)
            return {"results": []}

    async def search_movies(
        self, query: str, language: str = "eng", **kwargs
    ) -> Dict[str, Any]:
        """
        Search for movies on TVDB.

        Args:
            query: Movie name
            language: Language code

        Returns:
            Search results
        """
        params = {"query": query, "type": "movie"}

        try:
            data = await self._make_authenticated_request("search", params)

            results = []
            for item in data.get("data", []):
                results.append(
                    {
                        "id": item.get("tvdb_id"),
                        "title": item.get("name"),
                        "original_title": item.get("name"),
                        "overview": item.get("overview", ""),
                        "release_date": item.get("first_air_date", ""),
                        "poster_path": item.get("image_url", ""),
                        "media_type": "movie",
                    }
                )

            return {"results": results}

        except (aiohttp.ClientError, APIError, KeyError, ValueError) as exc:
            logger.exception("TVDB search movie failed", exc_info=exc)
            return {"results": []}

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Get item details from TVDB.

        Args:
            item_id: Item ID on TVDB.
            content_type: Content type (TV_SERIES or MOVIE).
            **kwargs: Additional arguments including 'language'.

        Returns:
            Dictionary with item details.

        Raises:
            ValueError: If content_type is not supported.
        """
        language = kwargs.get("language", "eng")

        if content_type == ContentType.TV_SERIES:
            return await self.get_series_details(item_id, language)
        elif content_type == ContentType.MOVIE:
            return await self.get_movie_details(item_id, language)
        else:
            raise ValueError(f"Unsupported type: {content_type}")

    async def get_series_details(
        self, series_id: str, language: str = "eng"
    ) -> Dict[str, Any]:
        """Get series details from TVDB.

        Args:
            series_id: TVDB series ID.
            language: Language code (e.g., 'eng', 'fra').

        Returns:
            Dictionary with series details including seasons.
        """
        try:
            data = await self._make_authenticated_request(
                f"series/{series_id}/extended"
            )
            series_data = data.get("data", {})

            seasons_data = series_data.get("seasons", [])
            seasons = []

            for season in seasons_data:
                seasons.append(
                    {
                        "name": f"Season {season.get('number', 0)}",
                        "season_number": season.get("number", 0),
                        "episode_count": season.get("numberOfEpisodes", 0),
                        "overview": season.get("overview", ""),
                        "poster_path": season.get("image", ""),
                    }
                )

            return {
                "id": series_data.get("id"),
                "name": series_data.get("name"),
                "overview": series_data.get("overview", ""),
                "first_air_date": series_data.get("firstAired", ""),
                "status": series_data.get("status", {}).get("name", ""),
                "seasons": seasons,
                "genres": [g.get("name", "") for g in series_data.get("genres", [])],
                "network": series_data.get("originalNetwork", {}).get("name", ""),
                "poster_path": series_data.get("image", ""),
            }

        except (aiohttp.ClientError, APIError, KeyError, ValueError, TypeError) as exc:
            logger.exception("Error retrieving TVDB series", exc_info=exc)
            return {}

    async def get_movie_details(
        self, movie_id: str, language: str = "eng"
    ) -> Dict[str, Any]:
        """Get movie details from TVDB.

        Args:
            movie_id: TVDB movie ID.
            language: Language code.

        Returns:
            Dictionary with movie details.
        """
        try:
            data = await self._make_authenticated_request(f"movies/{movie_id}/extended")
            movie_data = data.get("data", {})

            return {
                "id": movie_data.get("id"),
                "title": movie_data.get("name"),
                "overview": movie_data.get("overview", ""),
                "release_date": movie_data.get("first_air_date", ""),
                "runtime": movie_data.get("runtime", 0),
                "genres": [g.get("name", "") for g in movie_data.get("genres", [])],
                "poster_path": movie_data.get("image", ""),
            }

        except (aiohttp.ClientError, APIError, KeyError, ValueError, TypeError) as exc:
            logger.exception("Error retrieving TVDB movie", exc_info=exc)
            return {}

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """Get related items (episodes for series).

        Args:
            item_id: TVDB series ID.
            content_type: Content type (only TV_SERIES supported).
            **kwargs: Additional arguments including 'season_number'.

        Returns:
            List of episode dictionaries for TV_SERIES, empty list otherwise.
        """
        if content_type == ContentType.TV_SERIES:
            season_number = kwargs.get("season_number", 1)
            return await self.get_series_episodes(item_id, season_number)

        return []

    async def get_series_episodes(
        self, series_id: str, season_number: int, language: str = "eng"
    ) -> List[Dict[str, Any]]:
        """Get episodes for a season.

        Args:
            series_id: TVDB series ID.
            season_number: Season number to fetch.
            language: Language code.

        Returns:
            List of episode dictionaries in standardized format.
        """
        try:
            params = {"season": season_number, "page": 0}

            data = await self._make_authenticated_request(
                f"series/{series_id}/episodes/default", params
            )

            episodes = []
            for episode in data.get("data", {}).get("episodes", []):
                episodes.append(
                    {
                        "id": episode.get("id"),
                        "name": episode.get("name", "TBA"),
                        "season_number": episode.get("seasonNumber", season_number),
                        "episode_number": episode.get("number", 0),
                        "overview": episode.get("overview", ""),
                        "air_date": episode.get("aired", ""),
                        "runtime": episode.get("runtime", 0),
                        "still_path": episode.get("image", ""),
                    }
                )

            return episodes

        except (aiohttp.ClientError, APIError, KeyError, ValueError, TypeError) as exc:
            logger.exception("Error retrieving TVDB episodes", exc_info=exc)
            return []

    async def get_all_episodes(
        self, series_id: str, language: str = "eng"
    ) -> Dict[str, str]:
        """Get all episodes from all seasons.

        Args:
            series_id: Series ID.
            language: Language code.

        Returns:
            Dictionary mapping episode codes to titles.
        """
        try:
            details = await self.get_series_details(series_id, language)
            seasons = details.get("seasons", [])

            all_episodes = {}

            for season in seasons:
                season_num = season["season_number"]
                if season_num == 0:
                    continue

                episodes = await self.get_series_episodes(
                    series_id, season_num, language
                )

                for episode in episodes:
                    season_str = str(episode["season_number"]).zfill(2)
                    episode_str = str(episode["episode_number"]).zfill(2)
                    code = f"S{season_str}E{episode_str}"
                    all_episodes[code] = episode["name"]

            return all_episodes

        except (aiohttp.ClientError, APIError, KeyError, ValueError, TypeError) as exc:
            logger.exception("Error retrieving all TVDB episodes", exc_info=exc)
            return {}
