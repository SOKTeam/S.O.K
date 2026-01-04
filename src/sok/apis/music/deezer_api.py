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
Deezer API Implementation
Support for music search and metadata.
"""

from typing import Optional, Dict, List, Any
import aiohttp

from sok.apis.base_api import BaseAPI
from sok.core.interfaces import MediaType, ContentType
from sok.core.exceptions import APIError


class DeezerApi(BaseAPI):
    """
    Deezer API for music.
    No API key required for public search.
    """

    BASE_URL = "https://api.deezer.com"

    def __init__(self, api_key: str = ""):
        """
        Initialize Deezer API.

        Args:
            api_key: Not used but required by BaseAPI signature
        """
        super().__init__(api_key, self.BASE_URL)
        self.session: Optional[aiohttp.ClientSession] = None

    @property
    def supported_media_types(self) -> List[MediaType]:
        """Get supported media types.

        Returns:
            List containing MUSIC media type.
        """
        return [MediaType.MUSIC]

    @property
    def supported_content_types(self) -> List[ContentType]:
        """Get supported content types.

        Returns:
            List containing ALBUM, ARTIST, TRACK content types.
        """
        return [ContentType.ALBUM, ContentType.ARTIST, ContentType.TRACK]

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
        data: Optional[str] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the Deezer API.

        Args:
            endpoint: API endpoint path.
            params: Query parameters.
            headers: HTTP headers.
            method: HTTP method (GET, POST, etc.).
            data: Raw request data.
            json_data: JSON request body.

        Returns:
            API response as dictionary.

        Raises:
            APIError: If the request fails or returns an error.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.BASE_URL}/{endpoint}"
        session = self.session
        assert session is not None

        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                response_data: Dict[str, Any] = await response.json()

                if "error" in response_data:
                    raise APIError(
                        f"Deezer API error: {response_data['error'].get('message', 'Unknown error')}"
                    )

                return response_data
        except aiohttp.ClientError as e:
            raise APIError(f"Deezer request failed: {str(e)}")

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Search for music on Deezer.

        Args:
            query: Search query string.
            content_type: Type of content (ALBUM, ARTIST, TRACK).
            **kwargs: Additional parameters (limit).

        Returns:
            Dictionary containing search results.
        """
        limit = kwargs.get("limit", 20)
        results = []

        if content_type == ContentType.ALBUM:
            results = await self.search_album(query, limit)
        elif content_type == ContentType.ARTIST:
            results = await self.search_artist(query, limit)
        else:
            results = await self.search_album(query, limit)

        return {"results": results}

    async def search_album(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for albums on Deezer.

        Args:
            query: Album search query.
            limit: Maximum number of results.

        Returns:
            List of album dictionaries.
        """
        data = await self._make_request("search/album", {"q": query, "limit": limit})

        albums = []
        for result in data.get("data", []):
            albums.append(
                {
                    "id": str(result.get("id")),
                    "title": result.get("title", ""),
                    "artist": result.get("artist", {}).get("name", ""),
                    "poster_path": result.get("cover_xl"),
                    "release_date": "",
                    "overview": "",
                }
            )
        return albums

    async def search_artist(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for artists on Deezer.

        Args:
            query: Artist search query.
            limit: Maximum number of results.

        Returns:
            List of artist dictionaries.
        """
        data = await self._make_request("search/artist", {"q": query, "limit": limit})

        artists = []
        for result in data.get("data", []):
            artists.append(
                {
                    "id": str(result.get("id")),
                    "title": result.get("name", ""),
                    "name": result.get("name", ""),
                    "poster_path": result.get("picture_xl"),
                    "overview": "",
                }
            )
        return artists

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Get detailed information for an item.

        Args:
            item_id: Deezer item ID.
            content_type: Type of content (ALBUM, ARTIST).
            **kwargs: Additional parameters.

        Returns:
            Dictionary containing item details.
        """
        if content_type == ContentType.ALBUM:
            return await self.get_album_details(item_id)
        elif content_type == ContentType.ARTIST:
            return await self.get_artist_details(item_id)
        return {}

    async def get_album_details(self, album_id: str) -> Dict[str, Any]:
        """Get detailed album information.

        Args:
            album_id: Deezer album ID.

        Returns:
            Dictionary containing album details with tracks.
        """
        data = await self._make_request(f"album/{album_id}")

        tracks = []
        for i, t in enumerate(data.get("tracks", {}).get("data", []), 1):
            tracks.append(
                {
                    "title": t.get("title", ""),
                    "duration": t.get("duration", 0),
                    "track_number": i,
                    "url": t.get("link", ""),
                }
            )

        genres = [g.get("name") for g in data.get("genres", {}).get("data", [])]

        return {
            "id": str(data.get("id")),
            "title": data.get("title", ""),
            "artist": data.get("artist", {}).get("name", ""),
            "release_date": data.get("release_date", ""),
            "poster_path": data.get("cover_xl"),
            "genres": genres,
            "tracks": tracks,
            "url": data.get("link", ""),
        }

    async def get_artist_details(self, artist_id: str) -> Dict[str, Any]:
        """Get detailed artist information.

        Args:
            artist_id: Deezer artist ID.

        Returns:
            Dictionary containing artist details.
        """
        data = await self._make_request(f"artist/{artist_id}")

        return {
            "id": str(data.get("id")),
            "title": data.get("name", ""),
            "name": data.get("name", ""),
            "poster_path": data.get("picture_xl"),
            "nb_album": data.get("nb_album", 0),
            "nb_fan": data.get("nb_fan", 0),
            "url": data.get("link", ""),
        }

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """Get related items (tracks for an album).

        Args:
            item_id: Deezer item ID.
            content_type: Type of content.
            **kwargs: Additional parameters.

        Returns:
            List of tracks for albums, empty list otherwise.
        """
        if content_type == ContentType.ALBUM:
            details = await self.get_album_details(item_id)
            return details.get("tracks", [])
        return []
