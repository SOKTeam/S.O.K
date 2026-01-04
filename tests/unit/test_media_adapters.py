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

from sok.core.adapters.media_adapters import adapt_search_results, adapt_details
from sok.core.interfaces import ContentType


def test_adapt_search_results_movie_fields_preserved():
    raw = [
        {
            "id": "123",
            "title": "Inception",
            "poster_path": "/poster.jpg",
            "release_date": "2010-07-16",
        }
    ]

    out = adapt_search_results(ContentType.MOVIE, raw)

    assert out["results"][0]["id"] == "123"
    assert out["results"][0]["title"] == "Inception"
    assert out["results"][0]["poster_path"] == "/poster.jpg"
    assert out["results"][0]["release_date"] == "2010-07-16"
    assert out["results"][0]["media_type"] == "movie"


def test_adapt_search_results_series_defaults():
    raw = [
        {
            "id": "abc",
            "name": "Dark",
        }
    ]

    out = adapt_search_results(ContentType.TV_SERIES, raw)

    assert out["results"][0]["name"] == "Dark"
    assert out["results"][0]["media_type"] == "tv"


def test_adapt_details_adds_defaults_for_series():
    payload = {"name": "Dark"}
    out = adapt_details(ContentType.TV_SERIES, payload)

    assert out["name"] == "Dark"
    assert out.get("seasons") == []


def test_adapt_details_keeps_tracks_for_album():
    payload = {"name": "Album", "tracks": [{"title": "t1"}]}
    out = adapt_details(ContentType.ALBUM, payload)
    assert out["tracks"] == [{"title": "t1"}]
