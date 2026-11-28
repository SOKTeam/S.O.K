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
"""S.O.K Server converts the videos to MKV while renaming them, when asked."""

import time
from collections import namedtuple

import pytest
from fastapi.testclient import TestClient

from sok.server import renames
from sok.server.app import create_app
from sok.server.renames import GB

Usage = namedtuple("Usage", "total used free")


@pytest.fixture
def downloads(tmp_path):
    folder = tmp_path / "downloads"
    folder.mkdir()
    (folder / "Dune.2021.1080p.mp4").write_bytes(b"x" * 1000)
    (folder / "Dune.2021.1080p.fr.srt").write_text("1\n")
    return folder


@pytest.fixture
def client(tmp_path, downloads, fake_mkvmerge):
    (tmp_path / "movies").mkdir()
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
                    "movies": [str(tmp_path / "movies")],
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


def convert(client, on=True):
    client.patch("/api/settings", json={"settings": {"convert_to_mkv": on}})


def rename(client):
    answer = client.post("/api/renames", json={"type": "movies"})
    assert answer.status_code == 202, answer.json()
    return wait(client, "/api/renames/current", "rename")


def new_names(client):
    rows = client.get("/api/rows?type=movies").json()["rows"]
    return [file["new_name"] for row in rows for file in row["files"]]


def test_the_setting_is_off_and_says_whether_mkvmerge_is_there(client):
    answer = client.get("/api/settings").json()
    assert answer["settings"]["convert_to_mkv"] is False
    assert answer["mkvmerge"] is True

    convert(client)

    assert client.get("/api/settings").json()["settings"]["convert_to_mkv"] is True
    wrong = client.patch("/api/settings", json={"settings": {"convert_to_mkv": "yes"}})
    assert wrong.status_code == 422


def test_without_mkvmerge_the_settings_say_so(client, monkeypatch):
    monkeypatch.setenv("SOK_MKVMERGE", "/nowhere/mkvmerge")

    assert client.get("/api/settings").json()["mkvmerge"] is False


def test_the_new_name_ends_with_mkv_except_with_hard_links(client):
    assert new_names(client) == ["Dune (2021).mp4"]

    convert(client)
    assert new_names(client) == ["Dune (2021).mkv"]

    client.patch("/api/settings", json={"settings": {"file_mode": "link"}})
    assert new_names(client) == ["Dune (2021).mp4"]


def test_a_move_converts_and_deletes_the_original(
    client, downloads, tmp_path, fake_mkvmerge
):
    convert(client)

    result = rename(client)["result"]

    assert result["renamed"] == 1
    movies = tmp_path / "movies"
    assert sorted(p.name for p in movies.iterdir()) == [
        "Dune (2021).fr.srt",
        "Dune (2021).mkv",
    ]
    assert not (downloads / "Dune.2021.1080p.mp4").exists()
    files = client.get("/api/history").json()["operations"][0]["files"]
    video = next(f for f in files if f["target"].endswith(".mkv"))
    assert (video["mode"], video["converted"]) == ("move", True)


def test_undo_puts_the_mkv_back_where_the_video_was(client, downloads):
    convert(client)
    rename(client)
    operation = client.get("/api/history").json()["operations"][0]["id"]

    answer = client.post(f"/api/history/{operation}/undo", json={}).json()

    assert str(downloads / "Dune.2021.1080p.mkv") in answer["restored"]
    assert (downloads / "Dune.2021.1080p.mkv").exists()


def test_a_copy_keeps_the_original(client, downloads, tmp_path):
    client.patch("/api/settings", json={"settings": {"file_mode": "copy"}})
    convert(client)

    rename(client)

    assert (downloads / "Dune.2021.1080p.mp4").exists()
    assert (tmp_path / "movies" / "Dune (2021).mkv").exists()


def test_a_failed_conversion_stays_on_its_row(
    client, downloads, tmp_path, fake_mkvmerge
):
    convert(client)
    fake_mkvmerge.fail = True

    result = rename(client)["result"]

    assert result["renamed"] == 0
    assert "MKV conversion failed" in result["errors"][0]["error"]
    assert (downloads / "Dune.2021.1080p.mp4").exists()
    assert list((tmp_path / "movies").iterdir()) == []
    row = client.get("/api/rows?type=movies").json()["rows"][0]
    assert row["files"][0]["error"]["code"] == "failed"


def test_a_conversion_on_the_same_disk_needs_room(client, monkeypatch):
    monkeypatch.setattr(
        renames.shutil, "disk_usage", lambda path: Usage(100 * GB, 0, GB + 10)
    )
    convert(client)

    answer = client.post("/api/renames", json={"type": "movies"})

    # A move on the same disk takes no room, but the MKV is a new file.
    assert answer.status_code == 409
    assert answer.json()["detail"]["needed"] == "1000"
