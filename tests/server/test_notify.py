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
import json
import sys
import time

import pytest
from fastapi.testclient import TestClient

from sok.server.app import create_app


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
                "settings": {"language": "en"},
                "folders": {
                    "sources": [str(downloads)],
                    "movies": [str(tmp_path / "movies")],
                },
            },
        )
        yield client


@pytest.fixture
def calls(client):
    """The requests of the notifier, answered with the status of their host."""
    sent = Sent()
    statuses = {}

    async def request(method, url, headers, body):
        sent.append({"method": method, "url": url, "headers": headers, "body": body})
        return statuses.get(url.split("/")[2], 204)

    client.app.state.notifier._request = request
    sent.statuses = statuses
    return sent


class Sent(list):
    statuses: dict


ALL = {
    "discord_url": "https://discord.com/api/webhooks/1/abc",
    "jellyfin_url": "http://jellyfin:8096/",
    "jellyfin_key": "jelly-key",
    "plex_url": "http://plex:32400",
    "plex_token": "plex-token",
    "webhook_url": "https://hooks.example/sok",
}


def notify(client, **fields):
    answer = client.patch("/api/settings", json={"notifications": fields})
    assert answer.status_code == 200, answer.json()
    return answer.json()["notifications"]


def rename_dune(client):
    client.post("/api/scans")
    for _ in range(200):
        if client.get("/api/scans/current").json()["scan"]["status"] != "running":
            break
        time.sleep(0.02)
    assert client.post("/api/renames", json={"type": "movies"}).status_code == 202


def wait_for(sent, count):
    for _ in range(200):
        if len(sent) >= count:
            return
        time.sleep(0.02)
    raise AssertionError(f"{len(sent)} requests, not {count}")


@pytest.fixture(autouse=True)
def no_script(monkeypatch):
    monkeypatch.delenv("SOK_AFTER_RENAME", raising=False)


def test_the_secrets_are_never_sent_back(client):
    shown = notify(client, **ALL)

    assert shown["discord"] == {"set": True}
    assert shown["webhook"] == {"set": True}
    # The addresses lose their last slash.
    assert shown["jellyfin"] == {"url": "http://jellyfin:8096", "set": True}
    assert shown["plex"] == {"url": "http://plex:32400", "set": True}
    assert shown["script"] is False
    text = json.dumps(client.get("/api/settings").json())
    for secret in ("abc", "jelly-key", "plex-token", "hooks.example"):
        assert secret not in text


def test_an_empty_value_removes_a_target(client):
    notify(client, **ALL)

    shown = notify(client, discord_url="", plex_token="")

    assert shown["discord"] == {"set": False}
    assert shown["plex"] == {"url": "http://plex:32400", "set": False}


def test_wrong_notification_fields(client):
    for fields, code in [
        ({"discord_url": "discord.com/api/webhooks/1"}, "invalid_url"),
        ({"slack_url": "https://slack.com"}, "unknown_setting"),
    ]:
        answer = client.patch("/api/settings", json={"notifications": fields})
        assert answer.status_code == 422
        assert answer.json()["detail"]["code"] == code


def test_a_rename_reaches_every_target(client, calls):
    notify(client, **ALL)

    rename_dune(client)
    wait_for(calls, 4)

    by_host = {c["url"].split("/")[2]: c for c in calls}
    discord = by_host["discord.com"]["body"]["content"]
    assert discord.splitlines() == [
        "**S.O.K Server** · Movies",
        "Files renamed: 1",
        "• Dune (2021).mkv",
    ]
    jellyfin = by_host["jellyfin:8096"]
    assert (jellyfin["method"], jellyfin["url"]) == (
        "POST",
        "http://jellyfin:8096/Library/Refresh",
    )
    assert jellyfin["headers"] == {"X-Emby-Token": "jelly-key"}
    plex = by_host["plex:32400"]
    assert plex["url"] == "http://plex:32400/library/sections/all/refresh"
    assert plex["headers"] == {"X-Plex-Token": "plex-token"}
    event = by_host["hooks.example"]["body"]
    assert (event["event"], event["media_type"], event["auto"], event["renamed"]) == (
        "renamed",
        "movies",
        False,
        1,
    )
    assert event["files"][0]["to"].endswith("Dune (2021).mkv")


def test_a_target_that_fails_leaves_the_others(client, calls):
    notify(client, **ALL)
    calls.statuses["discord.com"] = 404
    notifier = client.app.state.notifier
    event = {"media_type": "movies", "auto": True, "renamed": 0, "files": []}

    results = client.portal.call(notifier.renamed, event)

    assert results == {
        "discord": "HTTP 404",
        "jellyfin": None,
        "plex": None,
        "webhook": None,
    }


def test_a_long_list_is_cut(client, calls):
    notify(client, discord_url=ALL["discord_url"])
    files = [{"from": f"/d/{n}.mkv", "to": f"/m/Movie {n}.mkv"} for n in range(12)]
    event = {"media_type": "movies", "auto": True, "renamed": 12, "files": files}

    client.portal.call(client.app.state.notifier.renamed, event)

    lines = calls[0]["body"]["content"].splitlines()
    assert lines[1] == "Files sorted automatically: 12"
    assert len(lines) == 2 + 10 + 1
    assert lines[-1] == "…and 2 more"


def test_testing_a_target(client, calls):
    test = "/api/settings/test-notification"
    assert client.post(test, json={"target": "plex"}).json() == {
        "ok": False,
        "error": "not_set",
    }
    notify(client, plex_url=ALL["plex_url"], plex_token="plex-token")

    assert client.post(test, json={"target": "plex"}).json() == {
        "ok": True,
        "error": None,
    }
    calls.statuses["plex:32400"] = 401
    assert client.post(test, json={"target": "plex"}).json() == {
        "ok": False,
        "error": "HTTP 401",
    }
    assert client.post(test, json={"target": "slack"}).status_code == 422


def test_the_script_gets_the_rename(client, tmp_path, monkeypatch):
    out = tmp_path / "out.json"
    script = tmp_path / "after.py"
    script.write_text(
        "import json, os, sys\n"
        f"open({str(out)!r}, 'w').write(json.dumps("
        "{'stdin': json.load(sys.stdin), 'type': os.environ['SOK_MEDIA_TYPE'],"
        " 'renamed': os.environ['SOK_RENAMED']}))\n"
    )
    monkeypatch.setenv("SOK_AFTER_RENAME", f"{sys.executable} {script}")
    assert client.get("/api/settings").json()["notifications"]["script"] is True

    rename_dune(client)
    for _ in range(200):
        if out.exists():
            break
        time.sleep(0.05)

    result = json.loads(out.read_text())
    assert (result["type"], result["renamed"]) == ("movies", "1")
    assert result["stdin"]["files"][0]["to"].endswith("Dune (2021).mkv")


def test_a_script_that_fails_says_why(client, tmp_path, monkeypatch):
    script = tmp_path / "fail.py"
    script.write_text(
        "import sys\nprint('no library here', file=sys.stderr)\nsys.exit(3)\n"
    )
    monkeypatch.setenv("SOK_AFTER_RENAME", f"{sys.executable} {script}")

    answer = client.post("/api/settings/test-notification", json={"target": "script"})

    assert answer.json() == {"ok": False, "error": "exit code 3: no library here"}


def test_the_messages_follow_the_language(client, calls):
    client.patch("/api/settings", json={"settings": {"language": "fr"}})
    notify(client, discord_url=ALL["discord_url"])

    client.post("/api/settings/test-notification", json={"target": "discord"})

    assert "S.O.K Server" in calls[0]["body"]["content"]
    assert calls[0]["body"]["content"] != "S.O.K Server: the notifications work."
