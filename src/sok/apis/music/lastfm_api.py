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
Last.fm API Implementation
Support for music search and metadata.
"""

from typing import Optional, Dict, List, Any
import aiohttp

from sok.apis.base_api import BaseAPI
from sok.core.interfaces import MediaType, ContentType
from sok.core.exceptions import APIError


class LastFMApi(BaseAPI):
    """Last.fm API for music.

    Provides search and metadata retrieval from Last.fm.

    Attributes:
        BASE_URL: The base URL for Last.fm API.
        api_key: The Last.fm API key.

    See Also:
        https://www.last.fm/api/intro
    """

    BASE_URL = "http://ws.audioscrobbler.com/2.0/"

    def __init__(self, api_key: str):
        """
        Initialize Last.fm API.

        Args:
            api_key: Last.fm API key
        """
        super().__init__(api_key, self.BASE_URL)
        self.api_key = api_key

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
        """Make a request to the Last.fm API.

        Overrides base implementation for Last.fm specifics.
        Endpoint defines the 'method' parameter.

        Args:
            endpoint: API method name.
            params: Query parameters.
            headers: HTTP headers.
            method: HTTP method (ignored, always GET).
            data: Raw data (unused).
            json_data: JSON data (unused).

        Returns:
            Response JSON data.

        Raises:
            APIError: If the request fails.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        if params is None:
            params = {}

        params["api_key"] = self.api_key
        params["format"] = "json"

        if endpoint:
            params["method"] = endpoint

        session = self.session
        assert session is not None

        try:
            async with session.get(self.BASE_URL, params=params) as response:
                response.raise_for_status()
                response_data: Dict[str, Any] = await response.json()

                if "error" in response_data:
                    raise APIError(
                        f"Last.fm API error: {response_data.get('message', 'Unknown error')}"
                    )

                return response_data
        except aiohttp.ClientError as e:
            raise APIError(f"Last.fm request failed: {str(e)}")

    def _extract_image(self, images: List[Dict[str, str]]) -> Optional[str]:
        """Extract the largest available image URL.

        Last.fm returns images with sizes: small, medium, large, extralarge, mega.

        Args:
            images: List of image dictionaries with 'size' and '#text' keys.

        Returns:
            URL of the largest available image, or None.
        """
        if not images or not isinstance(images, list):
            return None

        sizes = ["mega", "extralarge", "large", "medium", "small"]

        img_map = {
            img.get("size"): img.get("#text") for img in images if img.get("#text")
        }

        for size in sizes:
            if size in img_map and img_map[size]:
                return img_map[size]

        for img in images:
            if img.get("#text"):
                return img.get("#text")

        return None

    def _parse_duration(self, duration: Any) -> Optional[int]:
        """Convert duration from milliseconds to seconds.

        Args:
            duration: Duration in milliseconds (int or string).

        Returns:
            Duration in seconds, or None if conversion fails.
        """
        try:
            return int(duration) // 1000
        except (ValueError, TypeError):
            return None

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Search for music content.

        Args:
            query: Search query.
            content_type: Type of content (ALBUM, ARTIST, TRACK).
            **kwargs: Additional parameters including 'limit'.

        Returns:
            Dictionary with 'results' key containing search results.
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
        """Search for albums on Last.fm.

        Args:
            query: Album search query.
            limit: Maximum number of results.

        Returns:
            List of album dictionaries.
        """
        data = await self._make_request(
            "album.search", {"album": query, "limit": limit}
        )

        albums = []
        matches = data.get("results", {}).get("albummatches", {}).get("album", [])

        if isinstance(matches, dict):
            matches = [matches]

        for match in matches:
            name = match.get("name", "")
            artist = match.get("artist", "")

            if not name or not artist:
                continue

            unique_id = f"{artist}|{name}"

            albums.append(
                {
                    "id": unique_id,
                    "title": name,
                    "artist": artist,
                    "mbid": match.get("mbid", ""),
                    "poster_path": self._extract_image(
                        match.get("image", [])
                    ),  # Pour l'UI
                    "url": match.get("url", ""),
                }
            )

        return albums

    async def search_artist(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for artists on Last.fm.

        Args:
            query: Artist search query.
            limit: Maximum number of results.

        Returns:
            List of artist dictionaries.
        """
        data = await self._make_request(
            "artist.search", {"artist": query, "limit": limit}
        )

        artists = []
        matches = data.get("results", {}).get("artistmatches", {}).get("artist", [])

        if isinstance(matches, dict):
            matches = [matches]

        for match in matches:
            name = match.get("name", "")
            if not name:
                continue

            artists.append(
                {
                    "id": name,
                    "title": name,
                    "name": name,
                    "listeners": match.get("listeners", "0"),
                    "mbid": match.get("mbid", ""),
                    "poster_path": self._extract_image(match.get("image", [])),
                    "url": match.get("url", ""),
                }
            )

        return artists

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Retrieve details of an item.

        Note: For albums, item_id must be 'Artist|Album' as Last.fm needs both.

        Args:
            item_id: Item identifier.
            content_type: Type of content.
            **kwargs: Additional parameters.

        Returns:
            Dictionary with item details.
        """
        if content_type == ContentType.ALBUM:
            artist = ""
            album = ""

            if "|" in item_id:
                parts = item_id.split("|", 1)
                artist = parts[0]
                album = parts[1]
            else:
                return await self._get_album_by_mbid(item_id)

            return await self.get_album_info(artist, album)

        elif content_type == ContentType.ARTIST:
            return await self.get_artist_info(item_id)

        return {}

    async def get_album_info(self, artist: str, album: str) -> Dict[str, Any]:
        """Get full album details by artist and album name.

        Args:
            artist: Artist name.
            album: Album name.

        Returns:
            Dictionary containing album details.
        """
        data = await self._make_request(
            "album.getinfo", {"artist": artist, "album": album, "autocorrect": 1}
        )
        return self._parse_album_details(data)

    async def _get_album_by_mbid(self, mbid: str) -> Dict[str, Any]:
        """Get full album details by MusicBrainz ID.

        Args:
            mbid: MusicBrainz album ID.

        Returns:
            Dictionary containing album details.
        """
        data = await self._make_request("album.getinfo", {"mbid": mbid})
        return self._parse_album_details(data)

    def _parse_album_details(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse album.getinfo response into standardized format.

        Args:
            data: Raw Last.fm API response.

        Returns:
            Normalized album data dictionary.
        """
        album_data = data.get("album", {})
        if not album_data:
            return {}

        tracks = []
        track_list = album_data.get("tracks", {}).get("track", [])
        if isinstance(track_list, dict):
            track_list = [track_list]

        for i, t in enumerate(track_list, 1):
            tracks.append(
                {
                    "title": t.get("name", ""),
                    "duration": self._parse_duration(t.get("duration", 0)),
                    "track_number": i,
                    "url": t.get("url", ""),
                }
            )

        tags_data = album_data.get("tags", {}).get("tag", [])
        if isinstance(tags_data, dict):
            tags_data = [tags_data]
        genres = [t.get("name", "") for t in tags_data]

        return {
            "id": album_data.get("mbid")
            or f"{album_data.get('artist')}|{album_data.get('name')}",
            "title": album_data.get("name", ""),
            "artist": album_data.get("artist", ""),
            "release_date": album_data.get("wiki", {})
            .get("published", "")
            .split(",")[0],
            "overview": album_data.get("wiki", {}).get("summary", ""),
            "poster_path": self._extract_image(album_data.get("image", [])),
            "genres": genres,
            "tracks": tracks,
            "url": album_data.get("url", ""),
        }

    async def get_artist_info(self, artist: str) -> Dict[str, Any]:
        """Get detailed artist information.

        Args:
            artist: Artist name.

        Returns:
            Dictionary containing artist details.
        """
        data = await self._make_request(
            "artist.getinfo", {"artist": artist, "autocorrect": 1}
        )
        artist_data = data.get("artist", {})

        if not artist_data:
            return {}

        tags_data = artist_data.get("tags", {}).get("tag", [])
        if isinstance(tags_data, dict):
            tags_data = [tags_data]
        genres = [t.get("name", "") for t in tags_data]

        return {
            "id": artist_data.get("name", ""),
            "title": artist_data.get("name", ""),
            "name": artist_data.get("name", ""),
            "overview": artist_data.get("bio", {}).get("summary", ""),
            "poster_path": self._extract_image(artist_data.get("image", [])),
            "genres": genres,
            "stats": artist_data.get("stats", {}),
            "similar": [
                s.get("name") for s in artist_data.get("similar", {}).get("artist", [])
            ],
        }

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """Retrieve related items.

        For an ALBUM, returns tracks.

        Args:
            item_id: Item identifier.
            content_type: Type of content.
            **kwargs: Additional parameters.

        Returns:
            List of related items.
        """
        if content_type == ContentType.ALBUM:
            details = await self.get_details(item_id, content_type)
            return details.get("tracks", [])
        return []
