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
from sok.core.media_manager import UniversalMediaManager
from sok.core.interfaces import ContentType, MediaType
from sok.core.exceptions import APIError, UnsupportedMediaTypeError


@pytest.mark.asyncio
async def test_search_wraps_api_errors_with_context():
    manager = UniversalMediaManager(load_defaults=False)
    failing_api = MagicMock()
    failing_api.supported_media_types = [MediaType.VIDEO]
    failing_api.search = AsyncMock(side_effect=RuntimeError("network down"))

    manager.register_api("tmdb_mock", failing_api)
    manager.set_current_api_for_media_type(MediaType.VIDEO, "tmdb_mock")

    with pytest.raises(APIError) as excinfo:
        await manager.search("matrix", ContentType.MOVIE)

    message = str(excinfo.value)
    assert "tmdb_mock" in message
    assert "network down" in message


@pytest.mark.asyncio
async def test_get_details_wraps_api_errors_with_context():
    manager = UniversalMediaManager(load_defaults=False)
    failing_api = MagicMock()
    failing_api.supported_media_types = [MediaType.VIDEO]
    failing_api.get_details = AsyncMock(side_effect=RuntimeError("timeout"))

    manager.register_api("tvdb_mock", failing_api)
    manager.set_current_api_for_media_type(MediaType.VIDEO, "tvdb_mock")

    with pytest.raises(APIError) as excinfo:
        await manager.get_details("123", ContentType.TV_SERIES)

    message = str(excinfo.value)
    assert "tvdb_mock" in message
    assert "timeout" in message


def test_get_current_api_falls_back_to_first_available():
    manager = UniversalMediaManager(load_defaults=False)
    api_a = MagicMock()
    api_a.supported_media_types = [MediaType.MUSIC]
    api_b = MagicMock()
    api_b.supported_media_types = [MediaType.MUSIC]

    manager.register_api("first", api_a)
    manager.register_api("second", api_b)

    chosen = manager.get_current_api(MediaType.MUSIC)
    assert chosen is api_a
    assert manager.current_apis[MediaType.MUSIC] == "first"


def test_set_current_api_rejects_unsupported_media_type():
    manager = UniversalMediaManager(load_defaults=False)
    api = MagicMock()
    api.supported_media_types = [MediaType.MUSIC]

    manager.register_api("music_only", api)

    with pytest.raises(UnsupportedMediaTypeError):
        manager.set_current_api_for_media_type(MediaType.VIDEO, "music_only")


def test_init_can_skip_default_loading():
    manager = UniversalMediaManager(load_defaults=False)
    assert manager.apis == {}
    assert manager.current_apis == {}
