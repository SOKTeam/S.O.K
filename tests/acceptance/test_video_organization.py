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
import os
from unittest.mock import AsyncMock, MagicMock
from sok.core.media_manager import UniversalMediaManager
from sok.core.interfaces import ContentType, MediaType
from sok.file_operations.base_operations import BaseFileOperations


class TestAcceptanceVideoOrganization:
    @pytest.mark.asyncio
    async def test_organize_movie_workflow(self, tmp_path):
        """
        Scenario: User organizes a movie file.
        1. Setup: A messy file exists.
        2. Action: User searches and selects metadata.
        3. Action: User applies rename.
        4. Result: File is renamed correctly.
        """
        # 1. Setup
        workspace = tmp_path / "downloads"
        workspace.mkdir()

        filename = "matrix.1999.mkv"
        file_path = workspace / filename
        file_path.write_text("dummy video content")

        # Initialize Core Logic
        manager = UniversalMediaManager()

        # Mock the TMDB API
        mock_api = MagicMock()
        mock_api.supported_media_types = [MediaType.VIDEO]

        # Mock Search Result
        mock_search_result = {
            "results": [
                {"id": 603, "title": "The Matrix", "release_date": "1999-03-30"}
            ]
        }
        mock_api.search = AsyncMock(return_value=mock_search_result)

        # Mock Details Result
        mock_details = {"id": 603, "title": "The Matrix", "release_date": "1999-03-30"}
        mock_api.get_details = AsyncMock(return_value=mock_details)

        # Register API
        manager.register_api("tmdb_mock", mock_api)
        manager.set_current_api_for_media_type(MediaType.VIDEO, "tmdb_mock")

        # 2. User Action: Identify/Search
        # Extract keywords (simulated user input or parser)
        search_query = "matrix"

        results = await manager.search(search_query, ContentType.MOVIE)
        assert len(results["results"]) > 0
        selected_movie = results["results"][0]
        assert selected_movie["title"] == "The Matrix"

        # 3. User Action: Generate New Name and Rename
        # Logic: Title + (Year) + Extension
        new_name = f"{selected_movie['title']} ({selected_movie['release_date'][:4]}){os.path.splitext(filename)[1]}"
        new_path = workspace / new_name

        # Perform Rename
        success = BaseFileOperations.safe_move(str(file_path), str(new_path))

        # 4. Verification
        assert success is True
        assert not os.path.exists(file_path)
        assert os.path.exists(new_path)
        assert new_path.name == "The Matrix (1999).mkv"
