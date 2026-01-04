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
Fanart.tv API implementation.

API Documentation: https://fanarttv.docs.apiary.io/
Note: Requires API key for full access. Personal key provides higher rate limits.
"""

from typing import Dict, List, Any
from sok.apis.base_api import BaseAPI
from sok.core.interfaces import MediaType, ContentType


class FanartApi(BaseAPI):
    """
    Fanart.tv API implementation for high-quality artwork.

    Provides access to fan-created artwork for movies, TV shows,
    music artists, and video games including posters, backgrounds,
    logos, and more.
    """

    def __init__(self, api_key: str):
        """Initialize Fanart.tv API.

        Args:
            api_key: Fanart.tv API key.
        """
        super().__init__(api_key, "https://webservice.fanart.tv/v3/")

    @property
    def supported_media_types(self) -> List[MediaType]:
        """Get supported media types.

        Returns:
            List containing VIDEO, MUSIC, GAME media types.
        """
        return [MediaType.VIDEO, MediaType.MUSIC, MediaType.GAME]

    @property
    def supported_content_types(self) -> List[ContentType]:
        """Get supported content types.

        Returns:
            List of MOVIE, TV_SERIES, ARTIST, ALBUM, GAME content types.
        """
        return [
            ContentType.MOVIE,
            ContentType.TV_SERIES,
            ContentType.ARTIST,
            ContentType.ALBUM,
            ContentType.GAME,
        ]

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """
        Fanart.tv doesn't support search - use TMDB/TVDB/MusicBrainz IDs directly.

        This method returns empty results as Fanart.tv requires external IDs.
        Use get_artwork_by_id() methods instead.
        """
        return {"results": []}

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Get artwork details for a media item.

        Args:
            item_id: External ID (TMDB, TVDB, or MusicBrainz).
            content_type: Type of content.
            **kwargs: Additional parameters.

        Returns:
            Artwork URLs and metadata.
        """
        if content_type == ContentType.MOVIE:
            return await self.get_movie_artwork(item_id)
        elif content_type == ContentType.TV_SERIES:
            return await self.get_tv_artwork(item_id)
        elif content_type in (ContentType.ARTIST, ContentType.ALBUM):
            return await self.get_music_artwork(item_id)
        elif content_type == ContentType.GAME:
            return await self.get_game_artwork(item_id)

        return {}

    async def get_movie_artwork(self, tmdb_id: str) -> Dict[str, Any]:
        """Get artwork for a movie using TMDB ID.

        Args:
            tmdb_id: TMDB movie ID.

        Returns:
            Movie artwork (posters, backgrounds, logos, etc.).
        """
        params = {"api_key": self.api_key}

        response = await self._make_request(f"movies/{tmdb_id}", params)

        return {
            "id": tmdb_id,
            "posters": self._extract_images(response.get("movieposter", [])),
            "backgrounds": self._extract_images(response.get("moviebackground", [])),
            "logos": self._extract_images(
                response.get("hdmovielogo", []) or response.get("movielogo", [])
            ),
            "cleararts": self._extract_images(
                response.get("hdmovieclearart", []) or response.get("movieclearart", [])
            ),
            "banners": self._extract_images(response.get("moviebanner", [])),
            "thumbs": self._extract_images(response.get("moviethumb", [])),
            "discs": self._extract_images(response.get("moviedisc", [])),
        }

    async def get_tv_artwork(self, tvdb_id: str) -> Dict[str, Any]:
        """Get artwork for a TV show using TVDB ID.

        Args:
            tvdb_id: TVDB series ID.

        Returns:
            TV show artwork (posters, backgrounds, logos, etc.).
        """
        params = {"api_key": self.api_key}

        response = await self._make_request(f"tv/{tvdb_id}", params)

        return {
            "id": tvdb_id,
            "posters": self._extract_images(response.get("tvposter", [])),
            "backgrounds": self._extract_images(response.get("showbackground", [])),
            "logos": self._extract_images(
                response.get("hdtvlogo", []) or response.get("clearlogo", [])
            ),
            "cleararts": self._extract_images(
                response.get("hdclearart", []) or response.get("clearart", [])
            ),
            "banners": self._extract_images(response.get("tvbanner", [])),
            "thumbs": self._extract_images(response.get("tvthumb", [])),
            "seasonposters": self._extract_season_images(
                response.get("seasonposter", [])
            ),
            "seasonbanners": self._extract_season_images(
                response.get("seasonbanner", [])
            ),
            "characterarts": self._extract_images(response.get("characterart", [])),
        }

    async def get_music_artwork(self, mbid: str) -> Dict[str, Any]:
        """Get artwork for a music artist using MusicBrainz ID.

        Args:
            mbid: MusicBrainz artist ID.

        Returns:
            Artist artwork (backgrounds, logos, thumbs, etc.).
        """
        params = {"api_key": self.api_key}

        response = await self._make_request(f"music/{mbid}", params)

        albums_artwork = {}
        for album in response.get("albums", {}).values():
            album_id = album.get("mbid_album", "")
            if album_id:
                albums_artwork[album_id] = {
                    "covers": self._extract_images(album.get("albumcover", [])),
                    "cds": self._extract_images(album.get("cdart", [])),
                }

        return {
            "id": mbid,
            "backgrounds": self._extract_images(response.get("artistbackground", [])),
            "logos": self._extract_images(
                response.get("hdmusiclogo", []) or response.get("musiclogo", [])
            ),
            "thumbs": self._extract_images(response.get("artistthumb", [])),
            "banners": self._extract_images(response.get("musicbanner", [])),
            "albums": albums_artwork,
        }

    async def get_game_artwork(self, game_id: str) -> Dict[str, Any]:
        """Get artwork for a video game.

        Args:
            game_id: Game ID (platform-specific).

        Returns:
            Game artwork dictionary.
        """
        params = {"api_key": self.api_key}

        try:
            response = await self._make_request(f"games/{game_id}", params)
        except Exception:
            return {"id": game_id}

        return {
            "id": game_id,
            "posters": self._extract_images(response.get("poster", [])),
            "backgrounds": self._extract_images(response.get("background", [])),
            "logos": self._extract_images(response.get("logo", [])),
            "cleararts": self._extract_images(response.get("clearart", [])),
            "banners": self._extract_images(response.get("banner", [])),
            "covers": self._extract_images(response.get("cover", [])),
        }

    def _extract_images(self, images: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract image URLs from API response.

        Args:
            images: List of image dictionaries from Fanart.tv.

        Returns:
            List of normalized image dictionaries sorted by likes.
        """
        results = []
        for img in images:
            results.append(
                {
                    "url": img.get("url", ""),
                    "language": img.get("lang", ""),
                    "likes": img.get("likes", 0),
                }
            )
        return sorted(results, key=lambda x: x.get("likes", 0), reverse=True)

    def _extract_season_images(
        self, images: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, str]]]:
        """Extract season-specific images grouped by season number.

        Args:
            images: List of season image dictionaries.

        Returns:
            Dictionary mapping season numbers to image lists.
        """
        seasons: Dict[str, List[Dict[str, str]]] = {}
        for img in images:
            season = img.get("season", "all")
            if season not in seasons:
                seasons[season] = []
            seasons[season].append(
                {
                    "url": img.get("url", ""),
                    "language": img.get("lang", ""),
                    "likes": img.get("likes", 0),
                }
            )
        return seasons

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """Get related items (not supported by Fanart.tv).

        Args:
            item_id: Item identifier.
            content_type: Type of content.
            **kwargs: Additional parameters.

        Returns:
            Empty list as Fanart.tv doesn't support related items.
        """
        return []
