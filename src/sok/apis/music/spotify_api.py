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
Spotify API Implementation
"""

import base64
import logging
import aiohttp
from typing import Dict, List, Any, Optional

from sok.core.interfaces import MediaType, ContentType
from sok.apis.base_api import BaseAPI
from sok.core.exceptions import APIError

logger = logging.getLogger(__name__)


class SpotifyApi(BaseAPI):
    """Spotify API implementation using Client Credentials Flow.

    Attributes:
        client_id: Spotify application client ID.
        client_secret: Spotify application client secret.
        access_token: Current OAuth access token.
    """

    def __init__(self, client_id: str, client_secret: str):
        """Initialize Spotify API.

        Args:
            client_id: Spotify application client ID.
            client_secret: Spotify application client secret.
        """
        super().__init__("", "https://api.spotify.com/v1/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None

    @property
    def supported_media_types(self) -> List[MediaType]:
        """Return supported media types.

        Returns:
            List containing MediaType.MUSIC.
        """
        return [MediaType.MUSIC]

    @property
    def supported_content_types(self) -> List[ContentType]:
        """Return supported content types.

        Returns:
            List containing ALBUM, TRACK, and ARTIST content types.
        """
        return [ContentType.ALBUM, ContentType.TRACK, ContentType.ARTIST]

    async def _get_access_token(self) -> str:
        """Get a Spotify access token.

        Returns:
            OAuth access token string.

        Raises:
            APIError: If authentication fails.
        """
        if not self.client_id or not self.client_secret:
            raise APIError("Spotify Client ID and Secret are required")

        auth_str = f"{self.client_id}:{self.client_secret}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://accounts.spotify.com/api/token", data=data, headers=headers
                ) as resp:
                    if resp.status != 200:
                        raise APIError(f"Spotify Auth Failed: {resp.status}")
                    json_data = await resp.json()
                    return json_data["access_token"]
        except aiohttp.ClientError as exc:
            logger.exception("Spotify auth HTTP error", exc_info=exc)
            raise APIError(f"Spotify Auth Error: {exc}") from exc
        except KeyError as exc:
            logger.exception("Spotify auth response missing access_token", exc_info=exc)
            raise APIError("Spotify Auth Error: missing access token") from exc

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
        data: Optional[str] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated request to Spotify API.

        Handles automatic token refresh on 401 errors.

        Args:
            endpoint: API endpoint path.
            params: Query parameters.
            headers: HTTP headers.
            method: HTTP method.
            data: Request body as string.
            json_data: Request body as JSON.

        Returns:
            API response as dictionary.
        """
        if not self.access_token:
            self.access_token = await self._get_access_token()

        if headers is None:
            headers = {}
        headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            return await super()._make_request(
                endpoint, params, headers, method, data, json_data
            )
        except APIError as exc:
            if "401" in str(exc):
                self.access_token = await self._get_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                return await super()._make_request(
                    endpoint, params, headers, method, data, json_data
                )
            logger.exception("Spotify API error", exc_info=exc)
            raise
        except aiohttp.ClientError as exc:
            logger.exception("Spotify HTTP error", exc_info=exc)
            raise APIError(f"Spotify request error: {exc}") from exc

    def _extract_image(self, images: List[Dict]) -> Optional[str]:
        """Extract first image URL from image list.

        Args:
            images: List of image dictionaries with 'url' keys.

        Returns:
            URL of the first image, or None if empty.
        """
        if images and len(images) > 0:
            return images[0].get("url")
        return None

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Search on Spotify.

        Args:
            query: Search query string.
            content_type: Type to search (ALBUM, TRACK, ARTIST).
            **kwargs: Additional parameters including 'limit'.

        Returns:
            Dictionary with 'results' list of matches.
        """
        type_mapping = {
            ContentType.ALBUM: "album",
            ContentType.TRACK: "track",
            ContentType.ARTIST: "artist",
        }

        spotify_type = type_mapping.get(content_type, "album")

        params = {"q": query, "type": spotify_type, "limit": kwargs.get("limit", 20)}

        data = await self._make_request("search", params)
        results = []

        if spotify_type == "album":
            items = data.get("albums", {}).get("items", [])
            for item in items:
                results.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("name"),
                        "artist": item.get("artists", [{}])[0].get("name", ""),
                        "poster_path": self._extract_image(item.get("images", [])),
                        "release_date": item.get("release_date", ""),
                        "total_tracks": item.get("total_tracks"),
                    }
                )

        elif spotify_type == "artist":
            items = data.get("artists", {}).get("items", [])
            for item in items:
                results.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("name"),
                        "name": item.get("name"),
                        "poster_path": self._extract_image(item.get("images", [])),
                        "popularity": item.get("popularity"),
                    }
                )

        return {"results": results}

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Get details for a Spotify item.

        Args:
            item_id: Spotify item ID.
            content_type: Type of item (ALBUM, TRACK, ARTIST).
            **kwargs: Additional parameters.

        Returns:
            Dictionary with item metadata.
        """
        type_mapping = {
            ContentType.ALBUM: "albums",
            ContentType.TRACK: "tracks",
            ContentType.ARTIST: "artists",
        }

        endpoint = f"{type_mapping.get(content_type, 'albums')}/{item_id}"
        data = await self._make_request(endpoint)

        if content_type == ContentType.ALBUM:
            tracks = []
            for i, t in enumerate(data.get("tracks", {}).get("items", []), 1):
                tracks.append(
                    {
                        "title": t.get("name"),
                        "track_number": t.get("track_number", i),
                        "duration": t.get("duration_ms", 0) // 1000,
                    }
                )

            return {
                "id": data.get("id"),
                "title": data.get("name"),
                "artist": data.get("artists", [{}])[0].get("name", ""),
                "poster_path": self._extract_image(data.get("images", [])),
                "tracks": tracks,
                "release_date": data.get("release_date", ""),
            }

        return data

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """Get related items (tracks for albums).

        Args:
            item_id: Spotify item ID.
            content_type: Content type (only ALBUM supported).
            **kwargs: Additional parameters.

        Returns:
            List of track dictionaries for ALBUM, empty list otherwise.
        """
        if content_type == ContentType.ALBUM:
            data = await self._make_request(f"albums/{item_id}/tracks")
            return data.get("items", [])
        return []
