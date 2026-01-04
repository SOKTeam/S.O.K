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
"""TMDB API client implementation.

Provides access to The Movie Database (TMDB) API for searching and retrieving
detailed metadata about movies and TV series.
"""

from typing import Dict, List, Any, Optional
from sok.apis.base_api import BaseAPI
from sok.core.interfaces import MediaType, ContentType


class TMDBApi(BaseAPI):
    """TMDB API implementation using JWT Bearer token (v4) for API v3.

    Attributes:
        session_id: Optional session ID for user actions.
        access_token: The TMDB v4 Read Access Token.
    """

    def __init__(self, access_token: str, session_id: Optional[str] = None):
        """Initializes the TMDB API.

        Args:
            access_token: The TMDB v4 Read Access Token (Bearer JWT)
            session_id: Optional Session ID for user actions
        """
        super().__init__(access_token, "https://api.themoviedb.org/3/")
        self.session_id = session_id
        self.access_token = access_token

    def _get_headers(self) -> Dict[str, str]:
        """Return headers with Bearer token.

        Returns:
            Dictionary with Authorization and Accept headers.
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def _get_base_params(self) -> Dict[str, Any]:
        """Return base parameters for requests.

        Returns:
            Dictionary with session_id if available.
        """
        params: Dict[str, Any] = {}
        if self.session_id:
            params["session_id"] = self.session_id
        return params

    @property
    def supported_media_types(self) -> List[MediaType]:
        """Return media types supported by TMDB.

        Returns:
            List containing MediaType.VIDEO.
        """
        return [MediaType.VIDEO]

    @property
    def supported_content_types(self) -> List[ContentType]:
        """Return content types supported by TMDB.

        Returns:
            List containing MOVIE and TV_SERIES content types.
        """
        return [ContentType.MOVIE, ContentType.TV_SERIES]

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Get details for a movie or series.

        Args:
            item_id: TMDB ID of the item.
            content_type: Type of content (MOVIE or TV_SERIES).
            **kwargs: Additional parameters including 'language'.

        Returns:
            Dictionary with item metadata.

        Raises:
            ValueError: If content_type is not supported.
        """
        language = kwargs.get("language", "en")

        if content_type == ContentType.MOVIE:
            return await self.get_movie_details(item_id, language)
        elif content_type == ContentType.TV_SERIES:
            return await self.get_tv_details(item_id, language)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """Get related items (episodes for a series).

        Args:
            item_id: TMDB ID of the series.
            content_type: Content type (only TV_SERIES supported).
            **kwargs: Additional parameters including 'language', 'season_number'.

        Returns:
            List of episode dictionaries for TV_SERIES, empty list otherwise.
        """
        language = kwargs.get("language", "en")
        season_number = kwargs.get("season_number", 1)

        if content_type == ContentType.TV_SERIES:
            return await self.get_tv_episodes(item_id, season_number, language)

        return []

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Search for movies or TV series.

        Args:
            query: Search query string.
            content_type: Type to search (MOVIE or TV_SERIES).
            **kwargs: Additional parameters including 'language'.

        Returns:
            Dictionary with 'results' list of matches.

        Raises:
            ValueError: If content_type is not supported.
        """
        if content_type == ContentType.MOVIE:
            return await self.search_movie(query, **kwargs)
        elif content_type == ContentType.TV_SERIES:
            return await self.search_tv(query, **kwargs)
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

    async def search_movie(self, title: str, language: str = "en") -> Dict[str, Any]:
        """Search for a movie on TMDB.

        Args:
            title: Movie title to search for.
            language: Language code for results.

        Returns:
            Dictionary with 'results' list of matching movies.
        """
        params = self._get_base_params()
        params.update({"query": title, "language": language, "page": 1})
        return await self._make_request("search/movie", params, self._get_headers())

    async def search_tv(self, title: str, language: str = "en") -> Dict[str, Any]:
        """Search for a TV series on TMDB.

        Args:
            title: Series title to search for.
            language: Language code for results.

        Returns:
            Dictionary with 'results' list of matching series.
        """
        params = self._get_base_params()
        params.update({"query": title, "language": language, "page": 1})
        return await self._make_request("search/tv", params, self._get_headers())

    async def get_movie_details(
        self, movie_id: str, language: str = "en"
    ) -> Dict[str, Any]:
        """Get detailed movie information.

        Args:
            movie_id: TMDB movie ID.
            language: Language code for results.

        Returns:
            Dictionary with movie metadata.
        """
        params = self._get_base_params()
        params["language"] = language
        return await self._make_request(
            f"movie/{movie_id}", params, self._get_headers()
        )

    async def get_tv_details(self, tv_id: str, language: str = "en") -> Dict[str, Any]:
        """Get detailed TV series information.

        Args:
            tv_id: TMDB series ID.
            language: Language code for results.

        Returns:
            Dictionary with series metadata.
        """
        params = self._get_base_params()
        params["language"] = language
        return await self._make_request(f"tv/{tv_id}", params, self._get_headers())

    async def get_tv_episodes(
        self, tv_id: str, season_number: int, language: str = "en"
    ) -> List[Dict[str, Any]]:
        """Get episodes for a season.

        Args:
            tv_id: TMDB series ID.
            season_number: Season number to fetch.
            language: Language code for results.

        Returns:
            List of episode dictionaries.
        """
        params = self._get_base_params()
        params["language"] = language
        result = await self._make_request(
            f"tv/{tv_id}/season/{season_number}", params, self._get_headers()
        )
        return result.get("episodes", [])
