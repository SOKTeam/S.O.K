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
IMDb API Implementation (via OMDb)
OMDb API (Open Movie Database) is a RESTful API for retrieving movie information.

Documentation: https://www.omdbapi.com/
Note: OMDb requires a free or paid API key depending on usage.
"""

import logging
from typing import Dict, List, Any, Optional
from sok.apis.base_api import BaseAPI
from sok.core.exceptions import APIError
from sok.core.interfaces import MediaType, ContentType

logger = logging.getLogger(__name__)


class IMDBApi(BaseAPI):
    """
    OMDb API implementation for accessing IMDb data.

    OMDb provides movie and TV series data from IMDb,
    with a simple and easy-to-use API.

    Note: The free API is limited to 1000 requests per day.
    """

    def __init__(self, api_key: str):
        """Initialize OMDb API.

        Args:
            api_key: OMDb API key.
        """
        super().__init__(api_key, "https://www.omdbapi.com/")

    @property
    def supported_media_types(self) -> List[MediaType]:
        """Get supported media types.

        Returns:
            List containing VIDEO media type.
        """
        return [MediaType.VIDEO]

    @property
    def supported_content_types(self) -> List[ContentType]:
        """Get supported content types.

        Returns:
            List containing MOVIE, TV_SERIES, and EPISODE content types.
        """
        return [ContentType.MOVIE, ContentType.TV_SERIES, ContentType.EPISODE]

    async def search(
        self, query: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Search on OMDb/IMDb.

        Args:
            query: Search term.
            content_type: Content type.
            **kwargs: Additional arguments (year, type, etc.).

        Returns:
            Search results in standardized format.
        """
        type_mapping = {
            ContentType.MOVIE: "movie",
            ContentType.TV_SERIES: "series",
            ContentType.EPISODE: "episode",
        }

        params = {
            "apikey": self.api_key,
            "s": query,
            "type": type_mapping.get(content_type, "movie"),
        }

        if kwargs.get("year"):
            params["y"] = kwargs["year"]

        try:
            data = await self._make_request("", params)

            if data.get("Response") == "False":
                logger.debug("OMDb: %s", data.get("Error", "No results"))
                return {"results": []}

            results = []
            for item in data.get("Search", []):
                normalized = {
                    "id": item.get("imdbID"),
                    "poster_path": item.get("Poster"),
                    "media_type": item.get("Type"),
                }

                if item.get("Type") == "movie":
                    normalized.update(
                        {
                            "title": item.get("Title"),
                            "original_title": item.get("Title"),
                            "release_date": item.get("Year"),
                        }
                    )
                else:  # series
                    normalized.update(
                        {
                            "name": item.get("Title"),
                            "original_name": item.get("Title"),
                            "first_air_date": item.get("Year"),
                        }
                    )

                results.append(normalized)

            return {"results": results}

        except (APIError, ValueError, KeyError) as exc:
            logger.exception("OMDb search failed", exc_info=exc)
            return {"results": []}

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> Dict[str, Any]:
        """Get item details via IMDb ID.

        Args:
            item_id: IMDb ID (e.g., 'tt0133093').
            content_type: Content type.

        Returns:
            Item details in standardized format.
        """
        params = {"apikey": self.api_key, "i": item_id, "plot": "full"}

        try:
            data = await self._make_request("", params)

            if data.get("Response") == "False":
                logger.debug("OMDb: %s", data.get("Error"))
                return {}

            if data.get("Type") == "movie":
                return self._normalize_movie_details(data)
            elif data.get("Type") == "series":
                return await self._normalize_series_details(data)

            return data

        except (APIError, ValueError, KeyError) as exc:
            logger.exception("OMDb details retrieval failed", exc_info=exc)
            return {}

    def _normalize_movie_details(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize movie details to standard format.

        Args:
            data: Raw OMDb data.

        Returns:
            Normalized data dictionary.
        """
        runtime = 0
        if data.get("Runtime") and data["Runtime"] != "N/A":
            try:
                runtime = int(data["Runtime"].split()[0])
            except (ValueError, TypeError):
                runtime = 0

        genres = []
        if data.get("Genre") and data["Genre"] != "N/A":
            genres = [{"name": g.strip()} for g in data["Genre"].split(",")]

        return {
            "id": data.get("imdbID"),
            "title": data.get("Title"),
            "original_title": data.get("Title"),
            "overview": data.get("Plot", ""),
            "release_date": data.get("Released", ""),
            "runtime": runtime,
            "genres": genres,
            "poster_path": data.get("Poster"),
            "vote_average": self._parse_rating(str(data.get("imdbRating"))),
            "vote_count": self._parse_votes(str(data.get("imdbVotes"))),
            "director": data.get("Director"),
            "actors": data.get("Actors"),
            "awards": data.get("Awards"),
            "box_office": data.get("BoxOffice"),
            "production": data.get("Production"),
            "website": data.get("Website"),
        }

    async def _normalize_series_details(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize TV series details to standard format.

        Args:
            data: Raw OMDb data.

        Returns:
            Normalized data with seasons.
        """
        genres = []
        if data.get("Genre") and data["Genre"] != "N/A":
            genres = [{"name": g.strip()} for g in data["Genre"].split(",")]

        total_seasons = 0
        if data.get("totalSeasons") and data["totalSeasons"] != "N/A":
            try:
                total_seasons = int(data["totalSeasons"])
            except (ValueError, TypeError):
                total_seasons = 0

        seasons = []
        for i in range(1, total_seasons + 1):
            seasons.append(
                {"name": f"Season {i}", "season_number": i, "episode_count": 0}
            )

        return {
            "id": data.get("imdbID"),
            "name": data.get("Title"),
            "original_name": data.get("Title"),
            "overview": data.get("Plot", ""),
            "first_air_date": data.get("Released", ""),
            "genres": genres,
            "seasons": seasons,
            "poster_path": data.get("Poster"),
            "vote_average": self._parse_rating(str(data.get("imdbRating"))),
            "vote_count": self._parse_votes(str(data.get("imdbVotes"))),
            "creator": data.get("Writer"),
            "actors": data.get("Actors"),
            "awards": data.get("Awards"),
            "network": data.get("Network", "N/A"),
        }

    def _parse_rating(self, rating_str: str) -> float:
        """Convert rating string to float.

        Args:
            rating_str: Rating as string (e.g., '8.5').

        Returns:
            Rating as float, or 0.0 if invalid.
        """
        try:
            if rating_str and rating_str != "N/A":
                return float(rating_str)
        except (ValueError, TypeError):
            return 0.0
        return 0.0

    def _parse_votes(self, votes_str: str) -> int:
        """Convert votes string to integer.

        Args:
            votes_str: Vote count as string (e.g., '1,234,567').

        Returns:
            Vote count as integer, or 0 if invalid.
        """
        try:
            if votes_str and votes_str != "N/A":
                return int(votes_str.replace(",", ""))
        except (ValueError, TypeError):
            return 0
        return 0

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs
    ) -> List[Dict[str, Any]]:
        """Get season episodes.

        Args:
            item_id: Series IMDb ID.
            content_type: Content type.
            **kwargs: season_number for episodes.

        Returns:
            Episodes list.
        """
        if content_type == ContentType.TV_SERIES:
            season_number = kwargs.get("season_number", 1)
            return await self.get_season_episodes(item_id, season_number)

        return []

    async def get_season_episodes(
        self, series_id: str, season_number: int
    ) -> List[Dict[str, Any]]:
        """Get episodes from specific season.

        Args:
            series_id: Series IMDb ID.
            season_number: Season number.

        Returns:
            Episodes list.
        """
        params = {"apikey": self.api_key, "i": series_id, "Season": season_number}

        try:
            data = await self._make_request("", params)

            if data.get("Response") == "False":
                logger.warning(
                    "OMDb episodes responded with error: %s", data.get("Error")
                )
                return []

            episodes = []
            for episode in data.get("Episodes", []):
                episodes.append(
                    {
                        "id": episode.get("imdbID"),
                        "name": episode.get("Title"),
                        "season_number": season_number,
                        "episode_number": int(episode.get("Episode", 0)),
                        "air_date": episode.get("Released"),
                        "vote_average": self._parse_rating(episode.get("imdbRating")),
                    }
                )

            return episodes

        except (APIError, ValueError, KeyError) as exc:
            logger.exception("Error retrieving OMDb episodes", exc_info=exc)
            return []

    async def search_by_title(
        self, title: str, year: Optional[int] = None, content_type: str = "movie"
    ) -> Optional[Dict[str, Any]]:
        """Direct search by exact title (faster).

        Args:
            title: Exact title.
            year: Release year.
            content_type: 'movie' or 'series'.

        Returns:
            Item details or None.
        """
        params = {
            "apikey": self.api_key,
            "t": title,
            "type": content_type,
            "plot": "full",
        }

        if year:
            params["y"] = str(year)

        try:
            data = await self._make_request("", params)

            if data.get("Response") == "False":
                return None

            return data

        except (APIError, ValueError, KeyError) as exc:
            logger.exception("Error searching by title OMDb", exc_info=exc)
            return None
