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

from sok.config import config_manager
from sok.config.api_registry import get_all_env_vars


@pytest.fixture(autouse=True)
def config_folder(tmp_path, monkeypatch):
    """Settings of their own for each test, never the user's ones."""
    folder = tmp_path / "config"
    monkeypatch.setenv("SOK_CONFIG_DIR", str(folder))
    monkeypatch.setattr(config_manager, "load_dotenv", lambda *a, **k: None)
    for variable in get_all_env_vars().values():
        monkeypatch.delenv(variable, raising=False)
    for name in ("SOK_AUTH", "SOK_USERNAME", "SOK_PASSWORD", "SOK_ENV_KEYS_WIN"):
        monkeypatch.delenv(name, raising=False)
    config_manager.reset_config_manager()
    yield folder
    config_manager.reset_config_manager()


class FakeVideoApi:
    async def get_tv_episodes(self, series_id, season, language):
        return [
            {"season_number": season, "episode_number": n, "name": f"Episode {n}"}
            for n in (1, 2, 3)
        ]


class FakeManager:
    """A media manager that answers from RESULTS, without the network."""

    RESULTS = {
        "dune": [
            {"id": 438631, "title": "Dune", "release_date": "2021-09-15"},
            {"id": 841, "title": "Dune", "release_date": "1984-12-14"},
        ],
        "the matrix": [
            {"id": 603, "title": "The Matrix", "release_date": "1999-03-31"}
        ],
        "severance": [
            {"id": 95396, "name": "Severance", "first_air_date": "2022-02-17"}
        ],
        "discovery daft punk": [
            {"id": 302127, "title": "Discovery", "artist": "Daft Punk"},
            {"id": 9, "title": "Discovery", "artist": "Data Punk"},
        ],
        "get lucky daft punk": [
            {
                "id": 67238735,
                "title": "Get Lucky",
                "artist": "Daft Punk",
                "album": "Random Access Memories",
                "track_number": 8,
                "release_date": "2013-05-17",
            }
        ],
        "dune frank herbert": [
            {"id": "B1", "title": "Dune", "authors": ["Frank Herbert"]},
            {"id": "B2", "title": "Dune", "authors": ["Frank Herbert"]},
        ],
        "chrono trigger": [
            {"id": 4205, "title": "Chrono Trigger", "release_date": "1995-03-11"}
        ],
    }

    def __init__(self, apis=("tmdb",), error=None):
        self.apis = list(apis)
        self.error = error
        # Errors of one content type only.
        self.errors = {}
        self.searches = []

    def get_available_apis_for_media_type(self, media_type):
        return self.apis

    def get_current_api(self, media_type):
        return FakeVideoApi()

    async def search(self, query, content_type, **kwargs):
        self.searches.append(query)
        error = self.errors.get(content_type) or self.error
        if error:
            raise error
        return {"results": self.RESULTS.get(query.lower(), [])}

    async def get_details(self, item_id, content_type, **kwargs):
        return {
            "id": item_id,
            "number_of_seasons": 1,
            "seasons": [{"season_number": 1, "name": "Season 1"}],
        }


@pytest.fixture(autouse=True)
def media_manager(monkeypatch):
    """The fake media manager of the server, for every test."""
    from sok.server import search

    manager = FakeManager()
    monkeypatch.setattr(search, "get_media_manager", lambda: manager)
    return manager
