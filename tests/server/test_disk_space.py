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
"""The room a rename of S.O.K Server needs on the disks it copies to."""

import time
from collections import namedtuple

import pytest
from fastapi.testclient import TestClient

from sok.server import renames
from sok.server.app import create_app
from sok.server.renames import GB, RenameError

Usage = namedtuple("Usage", "total used free")


@pytest.fixture
def downloads(tmp_path):
    folder = tmp_path / "downloads"
    folder.mkdir()
    (folder / "Dune.2021.1080p.mkv").write_text("Dune")
    return folder


@pytest.fixture
def client(tmp_path, downloads):
    (tmp_path / "movies").mkdir()
    with TestClient(create_app(tmp_path)) as client:
        client.post(
            "/api/setup", json={"username": "william", "password": "correct horse"}
        )
        client.patch(
            "/api/settings",
            json={
                "settings": {"language": "en", "file_mode": "copy"},
                "folders": {
                    "sources": [str(downloads)],
                    "movies": [str(tmp_path / "movies")],
                },
            },
        )
        client.post("/api/scans")
        for _ in range(200):
            if client.get("/api/scans/current").json()["scan"]["status"] != "running":
                break
            time.sleep(0.02)
        yield client


@pytest.fixture
def free(monkeypatch):
    """The free bytes of every disk, as the test sets them."""
    room = {"free": 10 * GB}
    monkeypatch.setattr(
        renames.shutil,
        "disk_usage",
        lambda path: Usage(100 * GB, 0, room["free"]),
    )
    return room


def rename(client):
    answer = client.post("/api/renames", json={"type": "movies"})
    if answer.status_code == 202:
        # Its end, before the next rename or the end of the test.
        for _ in range(200):
            current = client.get("/api/renames/current").json()["rename"]
            if current["status"] != "running":
                break
            time.sleep(0.02)
    return answer


def test_the_margin_is_one_gigabyte_and_can_change(client):
    assert client.get("/api/settings").json()["settings"]["free_space_margin_gb"] == 1
    client.patch("/api/settings", json={"settings": {"free_space_margin_gb": 20}})
    assert client.get("/api/settings").json()["settings"]["free_space_margin_gb"] == 20
    for wrong in (-1, 10_001, 1.5, True, "2"):
        answer = client.patch(
            "/api/settings", json={"settings": {"free_space_margin_gb": wrong}}
        )
        assert answer.status_code == 422


def test_a_copy_that_would_eat_the_margin_is_refused(client, free, tmp_path):
    free["free"] = GB + 2

    answer = rename(client)

    assert answer.status_code == 409
    detail = answer.json()["detail"]
    assert detail == {
        "code": "not_enough_space",
        "destination": str(tmp_path / "movies"),
        "needed": "4",
        "free": str(GB + 2),
        "margin": str(GB),
    }
    # Nothing was renamed.
    assert list((tmp_path / "movies").iterdir()) == []


def test_a_copy_with_room_is_renamed(client, free):
    free["free"] = GB + 4

    assert rename(client).status_code == 202


def test_no_margin_leaves_only_the_size_of_the_files(client, free):
    client.patch("/api/settings", json={"settings": {"free_space_margin_gb": 0}})
    free["free"] = 3

    assert rename(client).json()["detail"]["code"] == "not_enough_space"
    free["free"] = 4
    assert rename(client).status_code == 202


@pytest.mark.parametrize("mode", ["link", "move"])
def test_a_link_or_a_move_on_the_same_disk_needs_no_room(client, free, mode):
    client.patch("/api/settings", json={"settings": {"file_mode": mode}})
    free["free"] = 0

    assert rename(client).status_code == 202


def test_a_move_to_another_disk_needs_room(client, free, monkeypatch, downloads):
    client.patch("/api/settings", json={"settings": {"file_mode": "move"}})
    free["free"] = 0
    real_stat = renames.os.stat
    source = str(downloads / "Dune.2021.1080p.mkv")

    class OtherDisk:
        def __init__(self, stat):
            self.st_size = stat.st_size
            self.st_dev = stat.st_dev + 1

    monkeypatch.setattr(
        renames.os,
        "stat",
        lambda path, *a, **k: (
            OtherDisk(real_stat(path)) if str(path) == source else real_stat(path)
        ),
    )

    assert rename(client).json()["detail"]["code"] == "not_enough_space"


def test_the_automatic_sorting_tells_the_lack_of_room(client, free):
    sent = []

    async def request(method, url, headers, body):
        sent.append({"url": url, "body": body})
        return 204

    state = client.app.state
    state.notifier._request = request
    client.patch(
        "/api/settings",
        json={
            "notifications": {
                "discord_url": "https://discord.com/api/webhooks/1/abc",
                "jellyfin_url": "http://jellyfin:8096",
                "jellyfin_key": "jelly-key",
                "webhook_url": "https://hooks.example/sok",
            }
        },
    )
    free["free"] = 512 * 1024**2

    async def start():
        with pytest.raises(RenameError) as error:
            state.renamer.start("movies", auto=True)
        assert error.value.code == "not_enough_space"

    client.portal.call(start)
    for _ in range(200):
        if len(sent) >= 2:
            break
        time.sleep(0.02)

    hosts = sorted(call["url"].split("/")[2] for call in sent)
    # Jellyfin has nothing to refresh.
    assert hosts == ["discord.com", "hooks.example"]
    by_host = {call["url"].split("/")[2]: call["body"] for call in sent}
    assert by_host["discord.com"]["content"].splitlines()[1] == (
        f"Not sorted: not enough room on {state.settings.folders()['movies'][0]}"
        " (0.0 GB needed + 1.0 GB kept free, 0.5 GB free)."
    )
    event = by_host["hooks.example"]
    assert (event["event"], event["media_type"], event["auto"]) == (
        "not_enough_space",
        "movies",
        True,
    )
