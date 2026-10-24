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
import os

import pytest
from fastapi.testclient import TestClient

from sok.server.app import create_app
from sok.server.watcher import Watcher, snapshot


@pytest.fixture
def downloads(tmp_path):
    folder = tmp_path / "downloads"
    for name in [
        "Dune.2021.1080p.mkv",
        "Dune.mkv",
        "Severance/Season 1/Severance.S01E01.mkv",
        "Severance/Season 1/Severance.S01E02.mkv",
    ]:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    return folder


@pytest.fixture
def folders(tmp_path):
    names = ("movies", "tv")
    for name in names:
        (tmp_path / name).mkdir()
    return {name: tmp_path / name for name in names}


@pytest.fixture
def client(tmp_path, downloads, folders):
    with TestClient(create_app(tmp_path)) as client:
        client.post(
            "/api/setup", json={"username": "william", "password": "correct horse"}
        )
        client.patch(
            "/api/settings",
            json={
                "settings": {"language": "en", "auto_sort": True},
                "folders": {
                    "sources": [str(downloads)],
                    **{name: [str(path)] for name, path in folders.items()},
                },
            },
        )
        yield client


def check(client):
    """One pass of the watcher of the server, as its task runs it."""
    return client.portal.call(client.app.state.watcher.check)


def test_the_new_files_are_sorted_once_finished(client, downloads, folders):
    # The first check only learns the files: none is known as finished.
    assert check(client) is False
    assert client.get("/api/scans/current").json()["scan"] is None

    assert check(client) is True

    scan = client.get("/api/scans/current").json()["scan"]
    assert (scan["status"], scan["auto"]) == ("done", True)
    movie = folders["movies"] / "Dune (2021).mkv"
    assert os.path.samefile(movie, downloads / "Dune.2021.1080p.mkv")
    assert (folders["tv"] / "Severance" / "Season 1").is_dir()
    # The movie to pick waits in its tab.
    movies = client.get("/api/rows?type=movies").json()["rows"]
    assert [r["files"][0]["name"] for r in movies] == ["Dune.mkv"]
    assert client.get("/api/renames/current").json()["rename"]["auto"] is True
    run = client.get("/api/watch").json()["last_run"]
    assert (run["renamed"], run["errors"]) == (3, [])


def test_the_history_tells_an_automatic_rename(client, downloads, folders):
    check(client)
    check(client)

    operations = client.get("/api/history").json()["operations"]

    assert operations and all(op["auto"] for op in operations)


def test_nothing_new_starts_no_analysis(client):
    check(client)
    check(client)
    first = client.get("/api/scans/current").json()["scan"]["id"]

    assert check(client) is False

    assert client.get("/api/scans/current").json()["scan"]["id"] == first


def test_a_file_being_written_waits(client, downloads, folders):
    check(client)
    check(client)
    growing = downloads / "The.Matrix.1999.mkv"
    growing.write_text("part")
    check(client)
    growing.write_text("part and more")

    # Its size changed since the check before: not finished yet.
    assert check(client) is False
    assert not (folders["movies"] / "The Matrix (1999).mkv").exists()

    assert check(client) is True
    assert (folders["movies"] / "The Matrix (1999).mkv").exists()


def test_a_missing_destination_is_reported(client, downloads, folders):
    client.patch("/api/settings", json={"folders": {"tv": []}})
    check(client)

    check(client)

    errors = client.get("/api/watch").json()["last_run"]["errors"]
    assert errors == [{"media_type": "tv", "code": "no_destination"}]
    assert (folders["movies"] / "Dune (2021).mkv").exists()


def test_the_settings_of_the_sorting(client):
    status = client.get("/api/watch").json()
    assert (status["enabled"], status["minutes"]) == (True, 5)

    for wrong in (0, 1441, "5", True):
        answer = client.patch(
            "/api/settings", json={"settings": {"auto_sort_minutes": wrong}}
        )
        assert answer.status_code == 422
    client.patch("/api/settings", json={"settings": {"auto_sort_minutes": 30}})

    assert client.get("/api/settings").json()["settings"]["auto_sort_minutes"] == 30


def test_the_sorting_is_off_by_default(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        client.post(
            "/api/setup", json={"username": "william", "password": "correct horse"}
        )
        assert client.get("/api/watch").json()["enabled"] is False


def test_the_pace_of_the_checks(client):
    now = [1000.0]
    app = client.app.state
    watcher = Watcher(
        app.db,
        app.settings,
        app.scans,
        app.renamer,
        app.jobs,
        app.events,
        clock=lambda: now[0],
    )
    assert watcher._due()
    client.portal.call(watcher.check)

    now[0] += 299
    assert not watcher._due()
    now[0] += 1
    assert watcher._due()
    client.patch("/api/settings", json={"settings": {"auto_sort": False}})
    assert not watcher._due()


def test_downloads_in_progress_and_hidden_files_are_left_out(tmp_path):
    for name in ["Dune.mkv", "Dune.mkv.part", "Big.mkv.!qB", ".hidden.mkv"]:
        (tmp_path / name).write_text(name)
    (tmp_path / ".trash").mkdir()
    (tmp_path / ".trash" / "Old.mkv").write_text("old")

    assert list(snapshot([str(tmp_path)])) == [str(tmp_path / "Dune.mkv")]


def test_the_watch_needs_a_login(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/api/watch").status_code == 401
