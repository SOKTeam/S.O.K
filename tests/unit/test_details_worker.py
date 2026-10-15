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
import asyncio

import pytest

from sok.ui.workers import details_worker
from sok.ui.workers.details_worker import DetailsWorker


class FakeConfig:
    def __init__(self, language):
        self._language = language

    def get(self, key, default=None):
        return self._language if key == "language" else default


class FakeTmdb:
    def __init__(self):
        self.episode_languages = []

    async def get_tv_episodes(self, tv_id, season_number, language="en"):
        self.episode_languages.append(language)
        return [{"season_number": season_number, "episode_number": 1, "name": "Pilot"}]


class FakeManager:
    def __init__(self):
        self.api = FakeTmdb()
        self.details_language = None

    async def get_details(self, item_id, content_type, language="en"):
        self.details_language = language
        return {"title": "Breaking Bad", "number_of_seasons": 2}

    def get_current_api(self, media_type):
        return self.api


@pytest.mark.parametrize(
    ("setting", "expected"), [("en", "en-EN"), ("de", "de-DE"), ("fr", "fr-FR")]
)
def test_episode_titles_use_the_settings_language(monkeypatch, setting, expected):
    manager = FakeManager()
    monkeypatch.setattr(details_worker, "get_media_manager", lambda: manager)
    worker = DetailsWorker(
        "1396", "tv", fetch_episodes=True, config=FakeConfig(setting)
    )

    details = asyncio.run(worker._get_details())

    assert manager.details_language == expected
    assert manager.api.episode_languages == [expected, expected]
    assert details["episodes"] == {"S01E01": "Pilot", "S02E01": "Pilot"}
