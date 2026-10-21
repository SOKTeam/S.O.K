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
import time

import pytest
from fastapi.testclient import TestClient

from sok.core.exceptions import APIAuthenticationError, APIRateLimitError
from sok.server.app import create_app


@pytest.fixture
def downloads(tmp_path):
    folder = tmp_path / "downloads"
    for name in [
        "Dune.2021.1080p.mkv",
        "Dune.mkv",
        "Unknown.Thing.2003.mkv",
        "Severance/Season 1/Severance.S01E01.mkv",
        "Severance/Season 1/Severance.S01E02.mkv",
    ]:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    return folder


@pytest.fixture
def client(tmp_path, downloads):
    movies = tmp_path / "movies"
    other = tmp_path / "other"
    movies.mkdir()
    other.mkdir()
    with TestClient(create_app(tmp_path)) as client:
        client.post(
            "/api/setup", json={"username": "william", "password": "correct horse"}
        )
        client.patch(
            "/api/settings",
            json={
                "settings": {"language": "en"},
                "folders": {
                    "sources": [str(downloads)],
                    "movies": [str(movies), str(other)],
                },
            },
        )
        yield client


def scan(client):
    client.post("/api/scans")
    for _ in range(200):
        summary = client.get("/api/scans/current").json()
        if summary["scan"]["status"] != "running":
            return summary
        time.sleep(0.02)
    raise AssertionError("the analysis did not end")


def rows(client, media_type):
    return {
        row["files"][0]["name"]: row
        for row in client.get(f"/api/rows?type={media_type}").json()["rows"]
    }


def test_the_analysis_searches_the_movies(client):
    assert scan(client)["scan"]["status"] == "done"

    movies = rows(client, "movies")
    dune = movies["Dune.2021.1080p.mkv"]
    assert dune["status"] == "ok"
    assert dune["candidates"][dune["selected"]]["year"] == 2021
    assert dune["files"][0]["new_name"] == "Dune (2021).mkv"
    # Two Dune without a year: the user picks one.
    assert movies["Dune.mkv"]["status"] == "ambiguous"
    assert movies["Unknown.Thing.2003.mkv"]["status"] == "missing"
    assert movies["Unknown.Thing.2003.mkv"]["files"][0]["new_name"] is None


def test_a_ready_series_gets_its_episode_titles(client):
    scan(client)

    series = rows(client, "tv")["Severance.S01E01.mkv"]

    assert series["status"] == "ok"
    assert series["episodes_found"] == 3
    assert [f["new_name"] for f in series["files"]] == [
        "Severance S01E01 Episode 1.mkv",
        "Severance S01E02 Episode 2.mkv",
    ]


def test_picking_a_candidate_makes_the_row_ready(client):
    scan(client)
    dune = rows(client, "movies")["Dune.mkv"]

    answer = client.patch(f"/api/rows/{dune['id']}", json={"selected": 1})

    assert answer.json()["status"] == "ok"
    assert answer.json()["files"][0]["new_name"] == "Dune (1984).mkv"


def test_the_destination_is_one_of_the_folders_of_its_type(client):
    scan(client)
    dune = rows(client, "movies")["Dune.mkv"]

    assert (
        client.patch(f"/api/rows/{dune['id']}", json={"destination": 1}).json()[
            "destination"
        ]
        == 1
    )
    assert (
        client.patch(f"/api/rows/{dune['id']}", json={"destination": 2}).json()[
            "detail"
        ]
        == "invalid_destination"
    )
    assert (
        client.patch(f"/api/rows/{dune['id']}", json={"selected": 9}).json()["detail"]
        == "invalid_selection"
    )


def test_a_row_is_searched_again_with_the_text_typed(client, media_manager):
    scan(client)
    unknown = rows(client, "movies")["Unknown.Thing.2003.mkv"]

    answer = client.post(
        f"/api/rows/{unknown['id']}/search", json={"query": "The Matrix"}
    ).json()

    assert media_manager.searches[-1] == "The Matrix"
    assert answer["query"] == "The Matrix"
    assert answer["candidates"][0]["title"] == "The Matrix"


def test_the_choices_survive_a_new_analysis(client):
    scan(client)
    dune = rows(client, "movies")["Dune.mkv"]
    client.patch(f"/api/rows/{dune['id']}", json={"selected": 1, "destination": 1})

    scan(client)

    again = rows(client, "movies")["Dune.mkv"]
    assert (again["selected"], again["destination"], again["status"]) == (1, 1, "ok")


def test_without_a_video_key_the_analysis_says_so(client, media_manager):
    media_manager.apis = []

    summary = scan(client)

    assert summary["scan"]["status"] == "failed"
    assert summary["scan"]["error"] == {"code": "missing_key", "service": "tmdb"}
    # The files are sorted all the same.
    assert summary["counts"]["movies"]["pending"] == 3


@pytest.mark.parametrize(
    "error, code",
    [
        (APIAuthenticationError("401", "TMDB"), "key_refused"),
        (APIRateLimitError("429", "TMDB"), "rate_limited"),
    ],
)
def test_a_refused_key_or_a_used_quota_stops_the_analysis(
    client, media_manager, error, code
):
    media_manager.error = error

    summary = scan(client)

    assert summary["scan"]["error"] == {"code": code, "service": "tmdb"}


def test_the_search_of_a_row_reports_a_missing_key(client, media_manager):
    scan(client)
    dune = rows(client, "movies")["Dune.mkv"]
    media_manager.apis = []

    answer = client.post(f"/api/rows/{dune['id']}/search", json={})

    assert answer.status_code == 409
    assert answer.json()["detail"] == {"code": "missing_key", "service": "tmdb"}


def test_wrong_rows(client):
    assert client.get("/api/rows?type=anime").json()["detail"] == "unknown_type"
    assert client.get("/api/rows/999").status_code == 404
    assert client.patch("/api/rows/999", json={}).status_code == 404


def test_progress_events_during_the_search(client):
    with client.stream("GET", "/api/events") as stream:
        lines = stream.iter_lines()
        next(lines), next(lines), next(lines)
        client.post("/api/scans")
        seen = []
        for line in lines:
            if line.startswith("event: "):
                seen.append(line.removeprefix("event: "))
            if seen.count("scan") >= 2:
                break

    assert "progress" in seen
