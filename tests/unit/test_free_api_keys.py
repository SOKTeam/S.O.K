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
from sok.core import media_manager
from sok.core.media_manager import UniversalMediaManager


class FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def manager_with(monkeypatch, **values):
    monkeypatch.setattr(
        media_manager, "get_config_manager", lambda: FakeConfig(**values)
    )
    for name in ("API_KEY_RAWG", "GOOGLE_BOOKS_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    return UniversalMediaManager()


def test_free_apis_get_their_key_when_there_is_one(monkeypatch):
    manager = manager_with(
        monkeypatch, api_key_rawg="rawg-key", google_books_api_key="books-key"
    )

    assert manager.apis["rawg"].api_key == "rawg-key"
    assert manager.apis["google_books"].api_key == "books-key"


def test_free_apis_still_work_without_a_key(monkeypatch):
    manager = manager_with(monkeypatch)

    for service in ("rawg", "google_books", "deezer", "musicbrainz", "openlibrary"):
        assert service in manager.apis
    assert manager.apis["rawg"].api_key == ""
