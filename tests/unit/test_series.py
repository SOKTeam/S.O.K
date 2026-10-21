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
from pathlib import Path

import pytest

from sok.core.batch import parse_series
from sok.core.exceptions import APIError
from sok.core.series import fetch_episode_titles, season_folders


def test_season_folders_keep_the_names_of_their_own():
    details = {
        "number_of_seasons": 3,
        "seasons": [
            {"season_number": 0, "name": "Specials"},
            {"season_number": 1, "name": "Season 1"},
            {"season_number": 2, "name": "The Return"},
            {"season_number": 2, "name": "Duplicate"},
            {"season_number": 3, "name": "Saison 3"},
        ],
    }

    assert season_folders(details, "Saison") == {
        "Saison 1": 1,
        "Saison 2 - The Return": 2,
        "Saison 3": 3,
    }


def test_a_series_without_seasons_has_no_folders():
    assert season_folders({}, "Season") == {}


class FakeApi:
    async def get_tv_episodes(self, series_id, season, language):
        if season == 2:
            raise APIError("down")
        return [
            {"season_number": season, "episode_number": 1, "name": f"{season}-1"},
            {"season_number": season, "episode_number": 2, "name": f"{season}-2"},
        ]


def test_episode_titles_skip_a_season_that_fails():
    episodes = asyncio.run(fetch_episode_titles(FakeApi(), "42", 3, "fr-FR"))

    assert episodes == {
        "S01E01": "1-1",
        "S01E02": "1-2",
        "S03E01": "3-1",
        "S03E02": "3-2",
    }


def test_an_api_without_episodes_gives_none():
    assert asyncio.run(fetch_episode_titles(object(), "42", 3, "en")) == {}


@pytest.mark.parametrize(
    "name, title, year",
    [
        ("Severance.S01E02.1080p.mkv", "Severance", None),
        ("Doctor.Who.2005.S01E01.mkv", "Doctor Who", 2005),
        ("/tv/Doctor Who (2005)/Season 1/01x01.mkv", "Doctor Who", 2005),
        ("/tv/The Office/Season 2/02x03.mkv", "The Office", None),
        ("/tv/1883/Season 1/01x01.mkv", "1883", None),
    ],
)
def test_parse_series(name, title, year):
    parsed = parse_series([Path(name)])

    assert (parsed.query, parsed.year) == (title, year)
