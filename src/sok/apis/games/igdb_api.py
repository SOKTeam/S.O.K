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
IGDB (Internet Game Database) API implementation.

API Documentation: https://api-docs.igdb.com/
Note: Requires Twitch Client ID and Access Token.
"""

from typing import Dict, List, Any
from sok.apis.base_api import BaseAPI
from sok.core.interfaces import MediaType, ContentType
from datetime import datetime


class IGDBApi(BaseAPI):
    """
    IGDB API implementation for video game metadata.

    Provides comprehensive game information including platforms,
    developers, publishers, release dates, and ratings.

    Note: Requires Twitch authentication (Client ID + Access Token).
    """

    def __init__(self, client_id: str, access_token: str):
        """Initialize IGDB API.

        Args:
            client_id: Twitch Client ID.
            access_token: Twitch Access Token.
        """
        super().__init__(access_token, "https://api.igdb.com/v4/")
        self.client_id = client_id

    @property
    def supported_media_types(self) -> List[MediaType]:
        """Get supported media types.

        Returns:
            List containing GAME media type.
        """
        return [MediaType.GAME]

    @property
    def supported_content_types(self) -> List[ContentType]:
        """Get supported content types.

        Returns:
            List containing GAME content type.
        """
        return [ContentType.GAME]

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for IGDB requests.

        Returns:
            Headers dict with Client-ID, Authorization, and Content-Type.
        """
        return {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "text/plain",
        }

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Search for games on IGDB.

        Args:
            query: Game title search query.
            content_type: Content type.
            **kwargs: Additional parameters (max_results).

        Returns:
            Search results with 'results' key.
        """
        limit = kwargs.get("max_results", 10)

        body = f"""
            search "{query}";
            fields name, summary, rating, first_release_date,
                   platforms.name, genres.name, cover.url;
            limit {limit};
        """

        response = await self._make_request(
            "games", headers=self._get_headers(), method="POST", data=body
        )

        results: List[Dict[str, Any]] = []
        if isinstance(response, list):
            for game in response:
                platforms = [p.get("name", "") for p in game.get("platforms", [])]
                genres = [g.get("name", "") for g in game.get("genres", [])]

                release_date = ""
                if game.get("first_release_date"):
                    release_date = datetime.fromtimestamp(
                        game["first_release_date"]
                    ).strftime("%Y-%m-%d")

                cover_url = ""
                if game.get("cover", {}).get("url"):
                    cover_url = "https:" + game["cover"]["url"].replace(
                        "t_thumb", "t_cover_big"
                    )

                results.append(
                    {
                        "id": str(game.get("id")),
                        "title": game.get("name"),
                        "overview": game.get("summary", ""),
                        "rating": game.get("rating"),
                        "release_date": release_date,
                        "platforms": platforms,
                        "genres": genres,
                        "poster_path": cover_url,
                    }
                )

        return {"results": results}

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Get detailed game information from IGDB.

        Args:
            item_id: IGDB game ID.
            content_type: Content type.
            **kwargs: Additional parameters.

        Returns:
            Detailed game information.
        """
        body = f"""
            where id = {item_id};
            fields name, summary, storyline, rating, aggregated_rating,
                   first_release_date, platforms.name, genres.name,
                   involved_companies.company.name, involved_companies.developer,
                   involved_companies.publisher, cover.url, screenshots.url,
                   game_modes.name, player_perspectives.name, themes.name;
        """

        response = await self._make_request(
            "games", headers=self._get_headers(), method="POST", data=body
        )

        if not isinstance(response, list) or not response:
            return {}

        game = response[0]

        platforms = [p.get("name", "") for p in game.get("platforms", [])]
        genres = [g.get("name", "") for g in game.get("genres", [])]
        themes = [t.get("name", "") for t in game.get("themes", [])]
        game_modes = [m.get("name", "") for m in game.get("game_modes", [])]

        developers = []
        publishers = []
        for company in game.get("involved_companies", []):
            company_name = company.get("company", {}).get("name", "")
            if company.get("developer"):
                developers.append(company_name)
            if company.get("publisher"):
                publishers.append(company_name)

        release_date = ""
        if game.get("first_release_date"):
            release_date = datetime.fromtimestamp(game["first_release_date"]).strftime(
                "%Y-%m-%d"
            )

        cover_url = ""
        if game.get("cover", {}).get("url"):
            cover_url = "https:" + game["cover"]["url"].replace(
                "t_thumb", "t_cover_big"
            )

        screenshots = []
        for screenshot in game.get("screenshots", []):
            if screenshot.get("url"):
                screenshots.append(
                    "https:" + screenshot["url"].replace("t_thumb", "t_screenshot_big")
                )

        return {
            "id": str(game.get("id")),
            "title": game.get("name"),
            "overview": game.get("summary", ""),
            "storyline": game.get("storyline", ""),
            "rating": game.get("rating"),
            "aggregated_rating": game.get("aggregated_rating"),
            "release_date": release_date,
            "platforms": platforms,
            "genres": genres,
            "themes": themes,
            "game_modes": game_modes,
            "developers": developers,
            "publishers": publishers,
            "poster_path": cover_url,
            "screenshots": screenshots,
        }

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """Get similar games from IGDB.

        Args:
            item_id: IGDB game ID.
            content_type: Content type.
            **kwargs: Additional parameters.

        Returns:
            List of similar games.
        """
        body = f"""
            where id = {item_id};
            fields similar_games.name, similar_games.cover.url;
        """

        response = await self._make_request(
            "games", headers=self._get_headers(), method="POST", data=body
        )

        if not isinstance(response, list) or not response:
            return []

        similar_games = response[0].get("similar_games", [])

        results = []
        for game in similar_games:
            cover_url = ""
            if game.get("cover", {}).get("url"):
                cover_url = "https:" + game["cover"]["url"].replace(
                    "t_thumb", "t_cover_big"
                )

            results.append(
                {
                    "id": str(game.get("id")),
                    "title": game.get("name"),
                    "poster_path": cover_url,
                }
            )

        return results
