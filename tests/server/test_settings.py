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

from sok.config.config_manager import get_config_manager
from sok.file_operations import base_operations
from sok.server.app import create_app
from sok.server import settings as server_settings
from sok.server.settings import DIFFERENT_DRIVES, NO_HARD_LINKS, check_link


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        client.post(
            "/api/setup", json={"username": "william", "password": "correct horse"}
        )
        yield client


@pytest.fixture
def folders(tmp_path):
    downloads = tmp_path / "downloads"
    movies = tmp_path / "movies"
    downloads.mkdir()
    movies.mkdir()
    (downloads / "dune.mkv").write_text("video")
    return str(downloads), str(movies)


def patch(client, **change):
    return client.patch("/api/settings", json=change)


def key(answer, name):
    for service in answer.json()["keys"]:
        for entry in service["keys"]:
            if entry["key"] == name:
                return entry
    raise KeyError(name)


def test_the_settings_need_a_login(client):
    client.post("/api/logout")

    assert client.get("/api/settings").status_code == 401


def test_a_new_server_links_by_default(client):
    assert client.get("/api/settings").json()["settings"]["file_mode"] == "link"


def test_settings_are_changed_and_saved(client, config_folder):
    answer = patch(
        client, settings={"file_mode": "copy", "movie_format": "{title} [{year}]"}
    )

    assert answer.status_code == 200
    assert answer.json()["settings"]["file_mode"] == "copy"
    assert get_config_manager().get("movie_format") == "{title} [{year}]"
    assert '"file_mode": "copy"' in (config_folder / "config.json").read_text()


@pytest.mark.parametrize(
    "change, code",
    [
        ({"theme": "dark"}, "unknown_setting"),
        ({"file_mode": "symlink"}, "invalid_value"),
        ({"skip_duplicates": "yes"}, "invalid_value"),
        ({"movie_format": "  "}, "invalid_value"),
        ({"language": "xx"}, "invalid_value"),
        ({"preferred_api_books": "tmdb"}, "invalid_value"),
    ],
)
def test_a_wrong_setting_is_refused(client, change, code):
    answer = patch(client, settings=change)

    assert answer.status_code == 422
    assert answer.json()["detail"]["code"] == code


def test_nothing_is_saved_when_one_part_is_wrong(client, folders):
    answer = patch(
        client,
        settings={"file_mode": "copy"},
        folders={"sources": [folders[0], "/does/not/exist"]},
    )

    assert answer.status_code == 422
    assert answer.json()["detail"] == {
        "code": "invalid_folder",
        "item": "/does/not/exist",
    }
    current = client.get("/api/settings").json()
    assert current["settings"]["file_mode"] == "link"
    assert current["folders"]["sources"] == []


def test_a_key_is_never_sent_back(client):
    answer = patch(client, keys={"api_key_tmdb_v4": "secret-token"})

    assert "secret-token" not in answer.text
    assert key(answer, "api_key_tmdb_v4") == {
        "key": "api_key_tmdb_v4",
        "set": True,
        "locked": False,
    }
    assert get_config_manager().get("api_key_tmdb_v4") == "secret-token"


def test_an_empty_value_removes_a_key(client):
    patch(client, keys={"api_key_tmdb_v4": "secret-token"})

    answer = patch(client, keys={"api_key_tmdb_v4": ""})

    assert not key(answer, "api_key_tmdb_v4")["set"]


def test_an_environment_key_is_locked(tmp_path, monkeypatch):
    monkeypatch.setenv("SOK_ENV_KEYS_WIN", "1")
    monkeypatch.setenv("API_KEY_TMDB_V4", "from-env")
    with TestClient(create_app(tmp_path)) as client:
        client.post(
            "/api/setup", json={"username": "william", "password": "correct horse"}
        )

        assert key(client.get("/api/settings"), "api_key_tmdb_v4") == {
            "key": "api_key_tmdb_v4",
            "set": True,
            "locked": True,
        }
        answer = patch(client, keys={"api_key_tmdb_v4": "typed"})
        assert answer.json()["detail"]["code"] == "key_locked"


def test_an_unknown_key_is_refused(client):
    assert patch(client, keys={"theme": "x"}).json()["detail"]["code"] == (
        "unknown_key"
    )


def test_the_folders_are_saved_in_order_without_duplicates(client, folders):
    downloads, movies = folders

    answer = patch(
        client,
        folders={"sources": [downloads, downloads + "/"], "movies": [movies]},
    )

    saved = answer.json()["folders"]
    assert saved["sources"] == [downloads]
    assert saved["movies"] == [movies]
    assert saved["tv"] == []


def test_an_unknown_folder_role_is_refused(client, folders):
    answer = patch(client, folders={"anime": [folders[0]]})

    assert answer.json()["detail"]["code"] == "unknown_folder_role"


def test_the_link_checks_follow_the_folders(client, folders):
    downloads, movies = folders

    answer = patch(client, folders={"sources": [downloads], "movies": [movies]})

    assert answer.json()["link_checks"] == [
        {
            "source": downloads,
            "destination": movies,
            "ok": True,
            "problem": None,
            "tested": True,
        }
    ]
    assert os.listdir(movies) == []
    patch(client, settings={"file_mode": "move"})
    assert client.get("/api/settings").json()["link_checks"] == []


def test_the_link_test(client, folders):
    answer = client.post(
        "/api/settings/test-link",
        json={"source": folders[0], "destination": folders[1]},
    )

    assert answer.json()["ok"]


def test_two_drives_cannot_link(folders, monkeypatch):
    real_stat = os.stat

    class Stat:
        def __init__(self, path):
            self.st_dev = 2 if "movies" in str(path) else 1

    monkeypatch.setattr(
        server_settings.os, "stat", lambda p: Stat(p) if p in folders else real_stat(p)
    )

    assert check_link(*folders).problem == DIFFERENT_DRIVES


def test_a_disk_without_hard_links(folders, monkeypatch):
    def no_link(src, dst):
        raise OSError(1, "Operation not permitted")

    monkeypatch.setattr(base_operations.os, "link", no_link)

    assert check_link(*folders).problem == NO_HARD_LINKS


def test_an_empty_source_is_only_compared_by_drive(tmp_path, folders):
    empty = tmp_path / "empty"
    empty.mkdir()

    check = check_link(str(empty), folders[1])

    assert check.ok
    assert not check.tested


def test_the_key_test_uses_the_saved_key(client, monkeypatch):
    from sok.server.api import settings as settings_api

    seen = []

    async def fake_check(service, key, secret=""):
        seen.append((service, key, secret))
        from sok.apis.key_check import KeyCheck

        return KeyCheck(service, "ok")

    monkeypatch.setattr(settings_api, "check_key", fake_check)
    patch(client, keys={"api_key_tmdb_v4": "saved-token"})

    answer = client.post("/api/settings/test-key", json={"service": "tmdb"})

    assert answer.json() == {"service": "tmdb", "status": "ok", "detail": ""}
    assert seen == [("tmdb", "saved-token", "")]
    assert "saved-token" not in answer.text

    client.post(
        "/api/settings/test-key",
        json={"service": "spotify", "key": " typed-id ", "secret": "typed-secret"},
    )
    assert seen[-1] == ("spotify", "typed-id", "typed-secret")


def test_the_key_test_needs_a_login(client):
    client.post("/api/logout")

    assert (
        client.post("/api/settings/test-key", json={"service": "tmdb"}).status_code
        == 401
    )


def test_the_preferred_service_of_a_media_type(client, monkeypatch):
    resets = []
    monkeypatch.setattr(
        "sok.server.api.settings.reset_media_manager", lambda: resets.append(1)
    )

    answer = patch(client, settings={"preferred_api_books": "openlibrary"})

    assert answer.json()["settings"]["preferred_api_books"] == "openlibrary"
    assert {"id": "openlibrary", "name": "Open Library"} in answer.json()["services"][
        "books"
    ]
    # The next search uses the new service.
    assert resets == [1]
