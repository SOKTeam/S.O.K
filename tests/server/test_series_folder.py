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
"""The folder a series already has in a TV destination of S.O.K Server."""

import time

import pytest
from fastapi.testclient import TestClient

from sok.server.app import create_app


@pytest.fixture
def downloads(tmp_path):
    folder = tmp_path / "downloads"
    for name in ["Severance.S02E01.mkv", "Severance.S02E02.mkv"]:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    return folder


@pytest.fixture
def roots(tmp_path):
    """Two TV destinations: /tv and /tv4k."""
    paths = [tmp_path / "tv", tmp_path / "tv4k"]
    for path in paths:
        path.mkdir()
    return paths


@pytest.fixture
def client(tmp_path, downloads, roots):
    with TestClient(create_app(tmp_path)) as client:
        client.post(
            "/api/setup", json={"username": "william", "password": "correct horse"}
        )
        client.patch(
            "/api/settings",
            json={
                "settings": {"language": "en", "file_mode": "move"},
                "folders": {
                    "sources": [str(downloads)],
                    "tv": [str(p) for p in roots],
                },
            },
        )
        yield client


def wait(client, url, key):
    for _ in range(200):
        answer = client.get(url).json()[key]
        if answer and answer["status"] != "running":
            return answer
        time.sleep(0.02)
    raise AssertionError(f"{url} did not end")


def scan(client):
    client.post("/api/scans")
    wait(client, "/api/scans/current", "scan")


def series(client):
    [row] = client.get("/api/rows?type=tv").json()["rows"]
    return row


def season(root, name, episodes=1):
    folder = root / name / "Season 1"
    folder.mkdir(parents=True)
    for number in range(1, episodes + 1):
        (folder / f"Severance S01E0{number}.mkv").write_text("x")
    return root / name


def test_a_series_without_a_folder_gets_a_new_one(client):
    scan(client)

    row = series(client)

    assert row["series_folder"] is None
    assert row["folder_pending"] is False
    assert row["files"][0]["new_name"].startswith("Severance/Season 2/")


def test_the_folder_found_by_its_name_is_used_with_its_destination(client, roots):
    season(roots[1], "severance (2022)", episodes=2)
    scan(client)

    row = series(client)

    assert row["destination"] == 1
    assert row["folder_pending"] is False
    assert row["series_folder"]["chosen"] == 0
    [match] = row["series_folder"]["matches"]
    assert match["how"] == "title"
    assert match["seasons"] == [1]
    assert match["episodes"] == 2
    assert row["files"][0]["new_name"].startswith("severance (2022)/Season 2/")


def test_the_episodes_go_into_the_existing_folder_never_renamed(client, roots):
    season(roots[1], "severance (2022)")
    scan(client)

    rename = client.post("/api/renames", json={"type": "tv"})
    assert rename.status_code == 202
    assert wait(client, "/api/renames/current", "rename")["status"] == "done"

    assert sorted(p.name for p in roots[1].iterdir()) == ["severance (2022)"]
    assert (roots[1] / "severance (2022)" / "Season 2").is_dir()
    assert not (roots[0] / "Severance").exists()


def test_an_id_beats_a_name(client, roots):
    season(roots[0], "Severance")
    season(roots[1], "Dissonance [tmdbid-95396]")
    scan(client)

    [match] = series(client)["series_folder"]["matches"]

    assert match["how"] == "id"
    assert match["source"] == "tmdb"
    assert match["path"] == str(roots[1] / "Dissonance [tmdbid-95396]")


def test_a_folder_of_another_series_is_left(client, roots):
    season(roots[0], "Severance [tmdbid-1]")
    scan(client)

    assert series(client)["series_folder"] is None


def test_several_folders_wait_for_a_choice(client, roots):
    season(roots[0], "Severance")
    season(roots[1], "Severance (2022)")
    scan(client)

    row = series(client)
    assert row["folder_pending"] is True
    assert row["series_folder"]["chosen"] is None
    # Counted with the rows to pick, and never renamed until then.
    counts = client.get("/api/scans/current").json()["counts"]["tv"]
    assert counts["ambiguous"] == 1
    assert counts["ok"] == 0
    answer = client.post("/api/renames", json={"type": "tv"})
    assert answer.json()["detail"] == "nothing_to_rename"

    picked = client.patch(f"/api/rows/{row['id']}", json={"folder": 1}).json()
    assert picked["folder_pending"] is False
    assert picked["destination"] == 1
    assert picked["files"][0]["new_name"].startswith("Severance (2022)/Season 2/")

    # The choice stays after a new analysis.
    scan(client)
    assert series(client)["series_folder"]["chosen"] == 1

    fresh = client.patch(f"/api/rows/{row['id']}", json={"folder": "new"}).json()
    assert fresh["series_folder"]["chosen"] == "new"
    assert fresh["files"][0]["new_name"].startswith("Severance/Season 2/")


def test_a_wrong_folder_choice(client, roots):
    scan(client)
    row = series(client)

    answer = client.patch(f"/api/rows/{row['id']}", json={"folder": 0})

    assert answer.json()["detail"] == "invalid_folder"


def test_the_folder_of_an_earlier_rename_is_found_again(client, roots):
    scan(client)
    row = series(client)
    folder = roots[0] / "My favourite show"
    folder.mkdir()
    searcher = client.app.state.searcher
    searcher.remember_folder(searcher._row(row["id"]), str(folder), "2026-11-27")

    scan(client)

    [match] = series(client)["series_folder"]["matches"]
    assert match["how"] == "history"
    assert match["path"] == str(folder)


def test_a_rename_remembers_the_folder_of_the_series(client, roots):
    scan(client)
    client.post("/api/renames", json={"type": "tv"})
    wait(client, "/api/renames/current", "rename")

    searcher = client.app.state.searcher
    assert searcher.known_folders({"tmdb": "95396"}) == [str(roots[0] / "Severance")]


def test_a_new_season_folder_follows_the_others(client, roots):
    folder = roots[0] / "Severance"
    (folder / "Saison 01").mkdir(parents=True)
    scan(client)

    assert series(client)["files"][0]["new_name"].startswith("Severance/Saison 02/")
