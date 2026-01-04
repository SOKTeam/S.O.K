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
MusicBrainz API implementation.

API Documentation: https://musicbrainz.org/doc/MusicBrainz_API
Note: Free API, no authentication required. Rate limit: 1 request/second.
"""

from typing import Dict, List, Any
from sok.apis.base_api import BaseAPI
from sok.core.interfaces import MediaType, ContentType


class MusicBrainzApi(BaseAPI):
    """
    MusicBrainz API implementation for music metadata.

    MusicBrainz is an open music encyclopedia that collects music metadata
    and makes it available to the public. No API key required.
    """

    USER_AGENT = "S.O.K/1.0 (https://github.com/sok-team/sok)"

    def __init__(self):
        """Initialize MusicBrainz API (no API key required)."""
        super().__init__("", "https://musicbrainz.org/ws/2/")

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
            List containing ALBUM, TRACK, ARTIST content types.
        """
        return [ContentType.ALBUM, ContentType.TRACK, ContentType.ARTIST]

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for MusicBrainz requests.

        Returns:
            Headers dict with User-Agent and Accept.
        """
        return {"User-Agent": self.USER_AGENT, "Accept": "application/json"}

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Search for music on MusicBrainz.

        Args:
            query: Search query.
            content_type: Type of content (ALBUM, TRACK, ARTIST).
            **kwargs: Additional parameters (max_results).

        Returns:
            Search results with 'results' key.
        """
        limit = kwargs.get("max_results", 10)

        if content_type == ContentType.ALBUM:
            return await self._search_releases(query, limit)
        elif content_type == ContentType.ARTIST:
            return await self._search_artists(query, limit)
        elif content_type == ContentType.TRACK:
            return await self._search_recordings(query, limit)

        return {"results": []}

    async def _search_releases(self, query: str, limit: int) -> Dict[str, Any]:
        """Search for album releases on MusicBrainz.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            Dictionary containing release search results.
        """
        params = {"query": query, "limit": limit, "fmt": "json"}

        response = await self._make_request(
            "release", params, headers=self._get_headers()
        )

        results = []
        for release in response.get("releases", []):
            artist_credit = release.get("artist-credit", [{}])
            artist_name = artist_credit[0].get("name", "") if artist_credit else ""

            results.append(
                {
                    "id": release.get("id"),
                    "title": release.get("title"),
                    "artist": artist_name,
                    "release_date": release.get("date", ""),
                    "country": release.get("country", ""),
                    "status": release.get("status", ""),
                    "barcode": release.get("barcode", ""),
                }
            )

        return {"results": results}

    async def _search_artists(self, query: str, limit: int) -> Dict[str, Any]:
        """Search for artists on MusicBrainz.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            Dictionary containing artist search results.
        """
        params = {"query": query, "limit": limit, "fmt": "json"}

        response = await self._make_request(
            "artist", params, headers=self._get_headers()
        )

        results = []
        for artist in response.get("artists", []):
            results.append(
                {
                    "id": artist.get("id"),
                    "name": artist.get("name"),
                    "type": artist.get("type", ""),
                    "country": artist.get("country", ""),
                    "disambiguation": artist.get("disambiguation", ""),
                    "begin_date": artist.get("life-span", {}).get("begin", ""),
                }
            )

        return {"results": results}

    async def _search_recordings(self, query: str, limit: int) -> Dict[str, Any]:
        """Search for track recordings on MusicBrainz.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            Dictionary containing recording search results.
        """
        params = {"query": query, "limit": limit, "fmt": "json"}

        response = await self._make_request(
            "recording", params, headers=self._get_headers()
        )

        results = []
        for recording in response.get("recordings", []):
            artist_credit = recording.get("artist-credit", [{}])
            artist_name = artist_credit[0].get("name", "") if artist_credit else ""

            releases = recording.get("releases", [{}])
            album = releases[0].get("title", "") if releases else ""

            results.append(
                {
                    "id": recording.get("id"),
                    "title": recording.get("title"),
                    "artist": artist_name,
                    "album": album,
                    "duration": recording.get("length", 0),
                }
            )

        return {"results": results}

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Get detailed information from MusicBrainz.

        Args:
            item_id: MusicBrainz ID (MBID).
            content_type: Type of content.
            **kwargs: Additional parameters.

        Returns:
            Detailed information dictionary.
        """
        if content_type == ContentType.ALBUM:
            return await self._get_release_details(item_id)
        elif content_type == ContentType.ARTIST:
            return await self._get_artist_details(item_id)
        elif content_type == ContentType.TRACK:
            return await self._get_recording_details(item_id)

        return {}

    async def _get_release_details(self, mbid: str) -> Dict[str, Any]:
        """Get detailed release information from MusicBrainz.

        Args:
            mbid: MusicBrainz release ID.

        Returns:
            Dictionary containing release details with tracks.
        """
        params = {"inc": "artists+recordings+labels+release-groups", "fmt": "json"}

        response = await self._make_request(
            f"release/{mbid}", params, headers=self._get_headers()
        )

        artist_credit = response.get("artist-credit", [{}])
        artist_name = artist_credit[0].get("name", "") if artist_credit else ""

        tracks = []
        for medium in response.get("media", []):
            for track in medium.get("tracks", []):
                tracks.append(
                    {
                        "position": track.get("position"),
                        "title": track.get("title"),
                        "duration": track.get("length", 0),
                    }
                )

        return {
            "id": response.get("id"),
            "title": response.get("title"),
            "artist": artist_name,
            "release_date": response.get("date", ""),
            "country": response.get("country", ""),
            "barcode": response.get("barcode", ""),
            "tracks": tracks,
            "track_count": len(tracks),
        }

    async def _get_artist_details(self, mbid: str) -> Dict[str, Any]:
        """Get detailed artist information from MusicBrainz.

        Args:
            mbid: MusicBrainz artist ID.

        Returns:
            Dictionary containing artist details.
        """
        params = {"inc": "releases+release-groups", "fmt": "json"}

        response = await self._make_request(
            f"artist/{mbid}", params, headers=self._get_headers()
        )

        return {
            "id": response.get("id"),
            "name": response.get("name"),
            "type": response.get("type", ""),
            "country": response.get("country", ""),
            "disambiguation": response.get("disambiguation", ""),
            "begin_date": response.get("life-span", {}).get("begin", ""),
            "end_date": response.get("life-span", {}).get("end", ""),
        }

    async def _get_recording_details(self, mbid: str) -> Dict[str, Any]:
        """Get detailed recording information from MusicBrainz.

        Args:
            mbid: MusicBrainz recording ID.

        Returns:
            Dictionary containing recording details.
        """
        params = {"inc": "artists+releases", "fmt": "json"}

        response = await self._make_request(
            f"recording/{mbid}", params, headers=self._get_headers()
        )

        artist_credit = response.get("artist-credit", [{}])
        artist_name = artist_credit[0].get("name", "") if artist_credit else ""

        return {
            "id": response.get("id"),
            "title": response.get("title"),
            "artist": artist_name,
            "duration": response.get("length", 0),
        }

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """Get related items (not supported by MusicBrainz).

        Args:
            item_id: MusicBrainz item ID.
            content_type: Type of content.
            **kwargs: Additional parameters.

        Returns:
            Empty list as MusicBrainz doesn't have this endpoint.
        """
        return []
