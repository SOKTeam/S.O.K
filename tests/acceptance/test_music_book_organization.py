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
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

from sok.core.media_manager import UniversalMediaManager
from sok.core.interfaces import ContentType, MediaType
from sok.core.exceptions import UnsupportedMediaTypeError
from sok.file_operations.base_operations import BaseFileOperations


class TestAcceptanceMusicAndBookOrganization:
    @pytest.mark.asyncio
    async def test_organize_music_track(self, tmp_path):
        """Acceptance flow: search track metadata then rename with artist-title."""
        workspace = tmp_path / "music"
        workspace.mkdir()
        filename = "01-track.mp3"
        file_path = workspace / filename
        file_path.write_text("dummy music content")

        manager = UniversalMediaManager(load_defaults=False)

        mock_api = MagicMock()
        mock_api.supported_media_types = [MediaType.MUSIC]
        mock_api.supported_content_types = [ContentType.TRACK]

        mock_search_result = {
            "results": [
                {
                    "id": "track1",
                    "name": "Bohemian Rhapsody",
                    "artist": "Queen",
                    "release_date": "1975-10-31",
                }
            ]
        }
        mock_api.search = AsyncMock(return_value=mock_search_result)

        mock_details = {
            "id": "track1",
            "title": "Bohemian Rhapsody",
            "artist": "Queen",
            "release_date": "1975-10-31",
        }
        mock_api.get_details = AsyncMock(return_value=mock_details)

        manager.register_api("music_mock", mock_api)
        manager.set_current_api_for_media_type(MediaType.MUSIC, "music_mock")

        results = await manager.search("bohemian", ContentType.TRACK)
        assert len(results["results"]) == 1
        track = results["results"][0]
        assert track["title"] == "Bohemian Rhapsody"
        assert track["artist"] == "Queen"

        details = await manager.get_details(track["id"], ContentType.TRACK)
        ext = os.path.splitext(filename)[1]
        new_name = f"{details['artist']} - {details['title']}{ext}"
        new_path = workspace / new_name

        success = BaseFileOperations.safe_move(str(file_path), str(new_path))

        assert success is True
        assert not os.path.exists(file_path)
        assert os.path.exists(new_path)
        assert new_path.name == "Queen - Bohemian Rhapsody.mp3"

    @pytest.mark.asyncio
    async def test_organize_book_workflow(self, tmp_path):
        """Acceptance flow: search book metadata then rename with title-author-year."""
        workspace = tmp_path / "books"
        workspace.mkdir()
        filename = "unknown_book.epub"
        file_path = workspace / filename
        file_path.write_text("dummy book content")

        manager = UniversalMediaManager(load_defaults=False)

        mock_api = MagicMock()
        mock_api.supported_media_types = [MediaType.BOOK]
        mock_api.supported_content_types = [ContentType.BOOK]

        mock_search_result = {
            "results": [
                {
                    "id": "book1",
                    "title": "The Pragmatic Programmer",
                    "authors": ["Andrew Hunt", "David Thomas"],
                    "published_date": "1999",
                }
            ]
        }
        mock_api.search = AsyncMock(return_value=mock_search_result)

        mock_details = {
            "id": "book1",
            "title": "The Pragmatic Programmer",
            "authors": ["Andrew Hunt", "David Thomas"],
            "published_date": "1999",
        }
        mock_api.get_details = AsyncMock(return_value=mock_details)

        manager.register_api("books_mock", mock_api)
        manager.set_current_api_for_media_type(MediaType.BOOK, "books_mock")

        results = await manager.search("pragmatic programmer", ContentType.BOOK)
        assert len(results["results"]) == 1
        book = results["results"][0]
        assert book["title"] == "The Pragmatic Programmer"
        assert book["authors"] == ["Andrew Hunt", "David Thomas"]

        details = await manager.get_details(book["id"], ContentType.BOOK)
        author = details["authors"][0] if details.get("authors") else "Unknown"
        ext = os.path.splitext(filename)[1]
        new_name = f"{details['title']} - {author} ({details['published_date']}){ext}"
        new_path = workspace / new_name

        success = BaseFileOperations.safe_move(str(file_path), str(new_path))

        assert success is True
        assert not os.path.exists(file_path)
        assert os.path.exists(new_path)
        assert new_path.name == "The Pragmatic Programmer - Andrew Hunt (1999).epub"

    @pytest.mark.asyncio
    async def test_search_without_registered_api_raises(self, tmp_path):
        """Negative: searching without a registered API should raise."""
        manager = UniversalMediaManager(load_defaults=False)
        with pytest.raises(UnsupportedMediaTypeError):
            await manager.search("anything", ContentType.TRACK)
