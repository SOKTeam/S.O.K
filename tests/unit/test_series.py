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
from sok.core.series import (
    BY_ID,
    BY_TITLE,
    SeriesIdentity,
    fetch_episode_titles,
    find_series_folders,
    folder_name_parts,
    nfo_ids,
    season_folders,
    series_identity,
)


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


# ------------------------------------------------------------ Existing folder


@pytest.mark.parametrize(
    "name, parts",
    [
        (
            "Breaking Bad (2008) [tvdbid-81189]",
            ("breakingbad", 2008, {"tvdb": "81189"}),
        ),
        ("Dark {tmdb-70523}", ("dark", None, {"tmdb": "70523"})),
        ("The.Office.2005", ("theoffice", 2005, {})),
        ("La Casa de Papel [1080p]", ("lacasadepapel", None, {})),
        # A title that is a year stays a title.
        ("1923", ("1923", None, {})),
    ],
)
def test_folder_name_parts(name, parts):
    assert folder_name_parts(name) == parts


def test_nfo_ids_read_kodi_and_jellyfin_files(tmp_path):
    (tmp_path / "tvshow.nfo").write_text(
        '<tvshow><uniqueid type="tvdb" default="true">81189</uniqueid>'
        "<tmdbid>1396</tmdbid><imdb_id>tt0903747</imdb_id></tvshow>"
    )

    assert nfo_ids(str(tmp_path)) == {
        "tvdb": "81189",
        "tmdb": "1396",
        "imdb": "tt0903747",
    }
    assert nfo_ids(str(tmp_path / "nothing")) == {}


def test_series_identity_from_tmdb_details():
    identity = series_identity(
        {"id": 71446, "name": "La casa de papel", "first_air_date": "2017-05-02"},
        {
            "original_name": "La casa de papel",
            "alternative_titles": {"results": [{"title": "Money Heist"}]},
            "external_ids": {"tvdb_id": 327417, "imdb_id": "tt6468322"},
        },
        "tmdb",
    )

    assert identity.year == 2017
    assert identity.titles == ["La casa de papel", "Money Heist"]
    assert identity.ids == {"tmdb": "71446", "tvdb": "327417", "imdb": "tt6468322"}


def test_series_identity_from_tvdb_details():
    identity = series_identity(
        {"id": 81189, "name": "Breaking Bad"},
        {
            "aliases": ["Breaking Bad: Reazioni collaterali"],
            "remote_ids": {"tmdb": "1396"},
        },
        "tvdb",
    )

    assert identity.titles == ["Breaking Bad", "Breaking Bad: Reazioni collaterali"]
    assert identity.ids == {"tvdb": "81189", "tmdb": "1396"}


def _identity(**kwargs):
    values = {
        "title": "La casa de papel",
        "year": 2017,
        "titles": ["La casa de papel", "Money Heist"],
        "ids": {"tmdb": "71446"},
    }
    values.update(kwargs)
    return SeriesIdentity(**values)


def test_a_folder_is_found_by_a_translated_title(tmp_path):
    first, second = tmp_path / "tv", tmp_path / "tv4k"
    (first / "Dune").mkdir(parents=True)
    (second / "Money Heist" / "Season 1").mkdir(parents=True)
    (second / "Money Heist" / "Season 1" / "E01.mkv").write_text("x")
    (second / "Money Heist" / "Season 02").mkdir()

    [match] = find_series_folders(_identity(), [str(first), str(second)])

    assert match.how == BY_TITLE
    assert match.title == "Money Heist"
    assert match.root == 1
    assert match.seasons == [1, 2]
    assert match.episodes == 1


def test_a_far_year_or_another_id_is_not_the_series(tmp_path):
    (tmp_path / "La Casa de Papel (1990)").mkdir()
    (tmp_path / "Money Heist [tmdbid-1]").mkdir()
    other = tmp_path / "La casa de papel"
    other.mkdir()
    (other / "tvshow.nfo").write_text("<tmdbid>2</tmdbid>")

    assert find_series_folders(_identity(), [str(tmp_path)]) == []


def test_the_surest_matches_only(tmp_path):
    (tmp_path / "La casa de papel").mkdir()
    tagged = tmp_path / "Haus des Geldes"
    tagged.mkdir()
    (tagged / "tvshow.nfo").write_text('<uniqueid type="tmdb">71446</uniqueid>')

    [match] = find_series_folders(_identity(), [str(tmp_path)])

    assert match.how == BY_ID
    assert match.source == "nfo"
    assert match.path == str(tagged)


def test_a_missing_destination_is_skipped(tmp_path):
    assert find_series_folders(_identity(), [str(tmp_path / "gone")]) == []
