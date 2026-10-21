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
RAWG API implementation.

API Documentation: https://rawg.io/apidocs
Note: Free API with rate limits (requires API key for higher limits).
"""

import re
from typing import Dict, Iterable, List, Any, Optional
from sok.apis.base_api import BaseAPI
from sok.core.interfaces import MediaType, ContentType

# Short console names RAWG sometimes appends to a title, as in
# "Pokemon: Emerald Version (GBA)".
PLATFORM_TAGS = set(
    "3ds dc ds gb gba gbc gc gcn genesis gg md n64 nds nes ngc pc ps ps1 ps2 "
    "ps3 ps4 ps5 psp psv psx saturn sms snes switch vita wii wiiu x360 xb1 "
    "xbox".split()
) | {"wii u", "xbox 360", "xbox one"}


def clean_title(
    name: Optional[str], platforms: Iterable[Optional[str]] = ()
) -> Optional[str]:
    """Remove a console name at the end of a RAWG title.

    Only a short console name or one of the game's own platforms is
    removed, so a real subtitle in parentheses is kept.

    Args:
        name: The title as RAWG gives it.
        platforms: Platform names of the game.

    Returns:
        The title without the console: "Pokemon: Emerald Version (GBA)"
        gives "Pokemon: Emerald Version".
    """
    tags = PLATFORM_TAGS | {p.casefold() for p in platforms if p}
    match = re.match(r"(.+?)\s*\(([^()]+)\)\s*$", name or "")
    if match and match.group(2).strip().casefold() in tags:
        return match.group(1)
    return name


class RAWGApi(BaseAPI):
    """RAWG Video Games Database API implementation.

    Provides access to 500,000+ games with detailed information
    including platforms, genres, developers, and user ratings.

    Attributes:
        api_key: RAWG API key for authenticated requests.
        base_url: Base URL for the RAWG API.

    Note:
        Free API with rate limits.
    """

    def __init__(self, api_key: str = ""):
        """Initialize RAWG API.

        Args:
            api_key: RAWG API key (optional for basic usage).
        """
        super().__init__(api_key, "https://api.rawg.io/api/")

    @property
    def supported_media_types(self) -> List[MediaType]:
        """Return supported media types.

        Returns:
            List containing MediaType.GAME.
        """
        return [MediaType.GAME]

    @property
    def supported_content_types(self) -> List[ContentType]:
        """Return supported content types.

        Returns:
            List containing ContentType.GAME.
        """
        return [ContentType.GAME]

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """RAWG does not support related items retrieval."""
        raise NotImplementedError("RAWG API does not support related items retrieval.")

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Search for games on RAWG.

        Args:
            query: Search query string.
            content_type: Content type (only GAME supported).
            **kwargs: Additional parameters including 'max_results'.

        Returns:
            Dictionary with 'results' list of matching games.
        """
        params = {"search": query, "page_size": kwargs.get("max_results", 10)}

        if self.api_key:
            params["key"] = self.api_key

        response = await self._make_request("games", params)

        results = []
        for game in response.get("results", []):
            platforms = [
                p.get("platform", {}).get("name") for p in game.get("platforms") or []
            ]
            results.append(
                {
                    "id": game.get("id"),
                    "title": clean_title(game.get("name"), platforms),
                    "release_date": game.get("released"),
                    "rating": game.get("rating"),
                    "platforms": platforms,
                    "genres": [g.get("name") for g in game.get("genres", [])],
                }
            )

        return {"results": results}

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Get detailed game information from RAWG.

        Args:
            item_id: RAWG game ID.
            content_type: Content type (only GAME supported).
            **kwargs: Additional parameters.

        Returns:
            Dictionary with game metadata.
        """
        params = {"key": self.api_key} if self.api_key else {}

        response = await self._make_request(f"games/{item_id}", params)
        platforms = [
            p.get("platform", {}).get("name") for p in response.get("platforms") or []
        ]

        return {
            "id": response.get("id"),
            "name": clean_title(response.get("name"), platforms),
            "description": response.get("description_raw"),
            "release_date": response.get("released"),
            "rating": response.get("rating"),
            "metacritic_score": response.get("metacritic"),
            "platforms": platforms,
            "genres": [g.get("name") for g in response.get("genres", [])],
            "developers": [d.get("name") for d in response.get("developers", [])],
            "publishers": [p.get("name") for p in response.get("publishers", [])],
            "esrb_rating": response.get("esrb_rating", {}).get("name")
            if response.get("esrb_rating")
            else None,
        }
