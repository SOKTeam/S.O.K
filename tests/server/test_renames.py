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
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sok.server import renames
from sok.server.app import create_app
from sok.server.jobs import Busy, Jobs
from sok.server.settings import DIFFERENT_DRIVES


@pytest.fixture
def downloads(tmp_path):
    folder = tmp_path / "downloads"
    for name in [
        "Dune.2021.1080p.mkv",
        "Dune.2021.1080p.fr.srt",
        "Dune.mkv",
        "Severance/Season 1/Severance.S01E01.mkv",
        "Severance/Season 1/Severance.S01E02.mkv",
        "Frank Herbert - Dune.epub",
    ]:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    return folder


@pytest.fixture
def folders(tmp_path):
    names = ("movies", "tv", "books")
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
                "settings": {"language": "en"},
                "folders": {
                    "sources": [str(downloads)],
                    **{name: [str(path)] for name, path in folders.items()},
                },
            },
        )
        client.post("/api/scans")
        wait(client, "/api/scans/current", "scan")
        yield client


def wait(client, url, key):
    for _ in range(200):
        answer = client.get(url).json()[key]
        if answer and answer["status"] != "running":
            return answer
        time.sleep(0.02)
    raise AssertionError(f"{url} did not end")


def rename(client, media_type, rows=None):
    answer = client.post("/api/renames", json={"type": media_type, "rows": rows})
    assert answer.status_code == 202, answer.json()
    return wait(client, "/api/renames/current", "rename")


def rows(client, media_type):
    return client.get(f"/api/rows?type={media_type}").json()["rows"]


def test_ready_movies_are_linked_with_their_subtitles(client, downloads, folders):
    rename_ = rename(client, "movies")

    assert rename_["status"] == "done"
    assert rename_["result"]["renamed"] == 1
    assert rename_["result"]["subtitles"] == 1
    target = folders["movies"] / "Dune (2021).mkv"
    # A hard link, the default of the server: the torrent keeps its file.
    assert os.path.samefile(target, downloads / "Dune.2021.1080p.mkv")
    assert (folders["movies"] / "Dune (2021).fr.srt").exists()
    # The renamed movie leaves the table; the one to pick stays.
    assert [r["files"][0]["name"] for r in rows(client, "movies")] == ["Dune.mkv"]


def test_a_series_goes_to_its_season_folder(client, folders):
    assert rename(client, "tv")["status"] == "done"

    season = folders["tv"] / "Severance" / "Season 1"
    assert sorted(p.name for p in season.iterdir()) == [
        "Severance S01E01 Episode 1.mkv",
        "Severance S01E02 Episode 2.mkv",
    ]
    assert rows(client, "tv") == []


def test_the_preview_shows_an_existing_season_folder(client, folders):
    (folders["tv"] / "Severance" / "Saison 01").mkdir(parents=True)

    names = [f["new_name"] for f in rows(client, "tv")[0]["files"]]

    assert names[0] == "Severance/Saison 01/Severance S01E01 Episode 1.mkv"


def test_only_the_rows_listed_are_renamed(client, folders):
    client.patch("/api/settings", json={"settings": {"file_mode": "move"}})
    dune = rows(client, "movies")
    ambiguous = next(r for r in dune if r["status"] != "ok")

    # A row that is not Ready is left out.
    answer = client.post(
        "/api/renames", json={"type": "movies", "rows": [ambiguous["id"]]}
    )

    assert answer.json()["detail"] == "nothing_to_rename"


def test_a_rename_is_one_operation_of_the_history(client, downloads, folders):
    client.patch("/api/settings", json={"settings": {"file_mode": "move"}})
    operation_id = rename(client, "movies")["result"]["operation"]

    history = client.get("/api/history").json()["operations"]

    assert [op["id"] for op in history] == [operation_id]
    assert history[0]["media_type"] == "movies"
    assert [f["mode"] for f in history[0]["files"]] == ["move", "move"]
    assert history[0]["files"][1]["follows"] == history[0]["files"][0]["target"]
    assert not (downloads / "Dune.2021.1080p.mkv").exists()


def test_undo_puts_the_files_back(client, downloads, folders):
    operation_id = rename(client, "movies")["result"]["operation"]

    answer = client.post(f"/api/history/{operation_id}/undo", json={}).json()

    assert len(answer["restored"]) == 2
    assert answer["operation"]["undone"]
    assert list(folders["movies"].iterdir()) == []
    # The link is deleted, the torrent keeps its file.
    assert (downloads / "Dune.2021.1080p.mkv").exists()


def test_undo_one_file_with_its_subtitles(client, folders):
    operation_id = rename(client, "tv")["result"]["operation"]

    answer = client.post(f"/api/history/{operation_id}/undo", json={"index": 0})

    assert answer.json()["operation"]["partly_undone"]
    season = folders["tv"] / "Severance" / "Season 1"
    assert [p.name for p in season.iterdir()] == ["Severance S01E02 Episode 2.mkv"]


def test_the_history_survives_a_restart(tmp_path, client):
    operation_id = rename(client, "movies")["result"]["operation"]
    client.__exit__(None, None, None)

    with TestClient(create_app(tmp_path)) as again:
        again.post(
            "/api/login", json={"username": "william", "password": "correct horse"}
        )
        history = again.get("/api/history").json()["operations"]

    assert [op["id"] for op in history] == [operation_id]


def test_wrong_undo(client):
    operation_id = rename(client, "movies")["result"]["operation"]

    assert client.post("/api/history/nope/undo", json={}).status_code == 404
    answer = client.post(f"/api/history/{operation_id}/undo", json={"index": 9})
    assert answer.json()["detail"] == "unknown_operation"


def test_a_file_already_there_stays_on_its_row(client, folders):
    client.patch("/api/settings", json={"settings": {"skip_duplicates": True}})
    (folders["movies"] / "Dune (2021).mkv").write_text("already here")

    rename_ = rename(client, "movies")

    assert rename_["result"]["renamed"] == 0
    dune = next(r for r in rows(client, "movies") if r["status"] == "ok")
    assert dune["files"][0]["error"]["code"] == "already_exists"


def test_a_hard_link_that_cannot_be_made_stops_the_rename(
    client, monkeypatch, downloads, folders
):
    monkeypatch.setattr(renames, "link_problem", lambda file, folder: DIFFERENT_DRIVES)

    answer = client.post("/api/renames", json={"type": "movies"})

    assert answer.status_code == 409
    assert answer.json()["detail"] == {
        "code": DIFFERENT_DRIVES,
        "source": str(downloads),
        "destination": str(folders["movies"]),
    }
    assert list(folders["movies"].iterdir()) == []


def test_wrong_renames(client):
    assert client.post("/api/renames", json={"type": "nope"}).status_code == 422
    assert (
        client.post("/api/renames", json={"type": "games"}).json()["detail"]
        == "nothing_to_rename"
    )
    client.patch("/api/settings", json={"folders": {"tv": []}})
    assert (
        client.post("/api/renames", json={"type": "tv"}).json()["detail"]
        == "no_destination"
    )


def test_books_are_renamed_into_their_author_folder(client, folders):
    assert rename(client, "books")["status"] == "done"

    assert (folders["books"] / "Frank Herbert").is_dir()


def test_one_job_at_a_time():
    async def work():
        pass

    async def run():
        jobs = Jobs()
        jobs.start("scan", work())

        with pytest.raises(Busy) as busy:
            jobs.check("rename")
        assert busy.value.code == "scan_running"
        with pytest.raises(Busy) as busy:
            jobs.start("scan", work())
        assert busy.value.code == "already_running"
        await jobs.wait()
        assert not jobs.running()

    asyncio.run(run())


def scan(client):
    client.post("/api/scans")
    return wait(client, "/api/scans/current", "scan")


def movie_names(client):
    return sorted(r["files"][0]["name"] for r in rows(client, "movies"))


def test_a_linked_file_is_left_out_of_the_next_analyses(client, downloads):
    rename(client, "movies")

    assert scan(client)["processed"] == 1
    assert movie_names(client) == ["Dune.mkv"]
    processed = client.get("/api/processed").json()["files"]
    assert [(p["path"], Path(p["target"]).name) for p in processed] == [
        (str(downloads / "Dune.2021.1080p.mkv"), "Dune (2021).mkv")
    ]


def test_an_undone_file_is_analyzed_again(client):
    operation_id = rename(client, "movies")["result"]["operation"]
    client.post(f"/api/history/{operation_id}/undo", json={})

    assert client.get("/api/processed").json()["files"] == []
    assert scan(client)["processed"] == 0
    assert movie_names(client) == ["Dune.2021.1080p.mkv", "Dune.mkv"]


def test_a_forgotten_file_is_analyzed_again(client, downloads):
    rename(client, "movies")
    path = str(downloads / "Dune.2021.1080p.mkv")

    answer = client.post("/api/processed/forget", json={"paths": [path]})

    assert answer.json() == {"forgotten": 1}
    scan(client)
    assert "Dune.2021.1080p.mkv" in movie_names(client)


def test_a_changed_file_is_analyzed_again(client, downloads):
    rename(client, "movies")
    # Another download under the same name.
    (downloads / "Dune.2021.1080p.mkv").unlink()
    (downloads / "Dune.2021.1080p.mkv").write_text("a new file, longer")

    scan(client)

    assert "Dune.2021.1080p.mkv" in movie_names(client)


def test_a_moved_file_is_not_kept_as_processed(client):
    client.patch("/api/settings", json={"settings": {"file_mode": "move"}})
    rename(client, "movies")

    assert client.get("/api/processed").json()["files"] == []
