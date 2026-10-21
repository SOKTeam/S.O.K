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

from sok.apis.music import musicbrainz_api
from sok.apis.music.deezer_api import DeezerApi
from sok.apis.music.lastfm_api import LastFMApi
from sok.apis.music.spotify_api import SpotifyApi
from sok.core.adapters.media_adapters import adapt_search_results
from sok.core.interfaces import ContentType

LOCKET = {
    "title": "Locket",
    "artist": "Crumb",
    "album": "Locket",
    "album_type": "ep",
    "release_date": "2017-06-23",
    "track_number": 4,
}


def test_adapter_keeps_album_and_track_number():
    [adapted] = adapt_search_results(ContentType.TRACK, [LOCKET])["results"]
    assert (adapted["album"], adapted["album_type"], adapted["track_number"]) == (
        "Locket",
        "ep",
        4,
    )


def test_musicbrainz_releases_put_the_first_release_first():
    def release(title, date, kind="Album", secondary=(), status="Official"):
        return {
            "title": title,
            "date": date,
            "status": status,
            "release-group": {"primary-type": kind, "secondary-types": list(secondary)},
        }

    releases = [
        release("SXSW", "2017-01-01", secondary=["Compilation"]),
        release("Live", "2016-01-01", secondary=["Live"]),
        release("warm songs", "2017-11-08"),
        release("Locket", "2017-06-23", kind="EP"),
        release("Bootleg", "2016", status="Bootleg"),
    ]

    ordered = sorted(releases, key=musicbrainz_api._release_rank)

    assert [r["title"] for r in ordered] == [
        "Locket",
        "warm songs",
        "Live",
        "SXSW",
        "Bootleg",
    ]
    assert musicbrainz_api._album_type(releases[0]["release-group"]) == "compilation"


@pytest.mark.parametrize(
    "api, response, expected_param",
    [
        (
            DeezerApi(),
            {
                "data": [
                    {
                        "id": 1,
                        "title": "Locket",
                        "artist": {"name": "Crumb"},
                        "album": {"title": "Locket"},
                    }
                ]
            },
            ("q", "Crumb Locket"),
        ),
        (
            LastFMApi("key"),
            {
                "results": {
                    "trackmatches": {"track": [{"name": "Locket", "artist": "Crumb"}]}
                }
            },
            ("artist", "Crumb"),
        ),
    ],
)
def test_music_apis_search_tracks_not_albums(api, response, expected_param):
    calls = []

    async def fake_request(endpoint, params=None, *args, **kwargs):
        calls.append((endpoint, params))
        return response

    api._make_request = fake_request

    result = asyncio.run(
        api.search("x", ContentType.TRACK, title="Locket", artist="Crumb")
    )

    assert "track" in calls[0][0]
    assert calls[0][1][expected_param[0]] == expected_param[1]
    assert result["results"][0]["title"] == "Locket"


def test_spotify_searches_tracks_with_field_filters():
    api = SpotifyApi("id", "secret")
    calls = []

    async def fake_request(endpoint, params=None, *args, **kwargs):
        calls.append(params)
        return {
            "tracks": {
                "items": [
                    {
                        "id": "1",
                        "name": "Locket",
                        "track_number": 4,
                        "artists": [{"name": "Crumb"}],
                        "album": {
                            "name": "Locket",
                            "album_type": "single",
                            "release_date": "2017-06-23",
                            "images": [],
                        },
                    }
                ]
            }
        }

    api._make_request = fake_request

    [result] = asyncio.run(
        api.search("x", ContentType.TRACK, title="Locket", artist="Crumb")
    )["results"]

    assert calls[0]["q"] == 'track:"Locket" artist:"Crumb"'
    assert (result["album"], result["track_number"], result["album_type"]) == (
        "Locket",
        4,
        "single",
    )
