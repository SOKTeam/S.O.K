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
import pytest
from unittest.mock import AsyncMock, MagicMock
from sok.apis.video.tmdb_api import TMDBApi


class TestTMDBMock:
    @pytest.fixture
    def tmdb_api(self):
        return TMDBApi(access_token="fake_token")

    @pytest.mark.asyncio
    async def test_search_movie_mock(self, tmdb_api):
        """Test searching for a movie with a mocked API response."""

        # Define the expected JSON response from TMDB
        mock_response_data = {
            "page": 1,
            "results": [
                {
                    "id": 550,
                    "title": "Fight Club",
                    "release_date": "1999-10-15",
                    "overview": "A ticking-time-bomb insomniac...",
                }
            ],
            "total_results": 1,
            "total_pages": 1,
        }

        # Mock aiohttp.ClientSession used in BaseAPI
        # We need to mock the context manager returned by session.get()
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_response_data)

        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.get.return_value = mock_context

        # Inject the mock session into the API instance
        # Note: In a real scenario, we might want to patch 'aiohttp.ClientSession' class
        # but injecting it directly if the class allows is easier.
        # BaseAPI initializes session in __aenter__ or _make_request.
        # We can manually set it for the test.
        tmdb_api.session = mock_session

        # Execute
        result = await tmdb_api.search_movie("Fight Club")

        # Verify
        assert result["results"][0]["title"] == "Fight Club"
        assert result["results"][0]["id"] == 550

        # Verify the call was made with correct params
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        url = call_args[0][0]
        kwargs = call_args[1]

        assert "search/movie" in url
        assert kwargs["params"]["query"] == "Fight Club"
        assert kwargs["headers"]["Authorization"] == "Bearer fake_token"

    @pytest.mark.asyncio
    async def test_get_movie_details_mock(self, tmdb_api):
        """Test getting movie details with a mocked API response."""

        mock_response_data = {
            "id": 550,
            "title": "Fight Club",
            "runtime": 139,
            "genres": [{"id": 18, "name": "Drama"}],
        }

        # Setup Mock
        mock_response = MagicMock()
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.get.return_value = mock_context

        tmdb_api.session = mock_session

        # Execute
        result = await tmdb_api.get_movie_details("550")

        # Verify
        assert result["title"] == "Fight Club"
        assert result["runtime"] == 139
        assert "movie/550" in mock_session.get.call_args[0][0]
