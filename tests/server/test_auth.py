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
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from sok.server.api.auth import require_login
from sok.server.app import create_app
from sok.server.auth import (
    COOKIE_NAME,
    MAX_FAILURES,
    WAIT_SECONDS,
    Accounts,
    TooManyAttempts,
)
from sok.server.db import MIGRATIONS, Database

PASSWORD = "correct horse"


def make_client(tmp_path):
    app = create_app(tmp_path)

    @app.get("/api/private", dependencies=[Depends(require_login)])
    def private() -> dict:
        return {"ok": True}

    return TestClient(app)


@pytest.fixture
def client(tmp_path):
    with make_client(tmp_path) as client:
        yield client


def setup(client, username="william", password=PASSWORD):
    return client.post("/api/setup", json={"username": username, "password": password})


def test_health_answers_without_login(client):
    answer = client.get("/api/health")

    assert answer.status_code == 200
    assert answer.json()["status"] == "ok"
    assert answer.json()["db"] == len(MIGRATIONS)


def test_the_first_visit_creates_the_account_and_logs_in(client):
    assert client.get("/api/session").json() == {
        "auth": "login",
        "account": False,
        "logged_in": False,
        "username": None,
        "language": "en",
    }

    answer = setup(client)

    assert answer.status_code == 201
    cookie = answer.headers["set-cookie"]
    assert COOKIE_NAME in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "Max-Age=2592000" in cookie
    assert client.get("/api/session").json()["logged_in"]
    assert client.get("/api/private").status_code == 200


def test_the_account_is_created_only_once(client):
    setup(client)

    assert setup(client, "other").status_code == 409


def test_a_short_password_is_refused(client):
    answer = setup(client, password="short")

    assert answer.status_code == 422
    assert answer.json()["detail"] == "invalid_account"


def test_the_private_routes_need_a_session(client):
    setup(client)
    client.post("/api/logout")

    answer = client.get("/api/private")

    assert answer.status_code == 401
    assert answer.json()["detail"] == "not_logged_in"


def test_login_and_logout(client):
    setup(client)
    client.cookies.clear()

    assert (
        client.post(
            "/api/login", json={"username": "william", "password": "wrong password"}
        ).json()["detail"]
        == "wrong_login"
    )
    assert (
        client.post(
            "/api/login", json={"username": "william", "password": PASSWORD}
        ).status_code
        == 200
    )
    assert client.get("/api/private").status_code == 200

    assert client.post("/api/logout").status_code == 204
    assert client.get("/api/private").status_code == 401


def test_too_many_failures_wait(client):
    setup(client)
    for _ in range(MAX_FAILURES):
        client.post("/api/login", json={"username": "william", "password": "nope"})

    answer = client.post(
        "/api/login", json={"username": "william", "password": PASSWORD}
    )

    assert answer.status_code == 429
    assert int(answer.headers["retry-after"]) <= WAIT_SECONDS


def test_the_wait_ends_after_30_seconds(tmp_path):
    now = [1000.0]
    accounts = Accounts(Database(tmp_path / "sok.db"), clock=lambda: now[0])
    accounts.create("william", PASSWORD)
    for _ in range(MAX_FAILURES):
        accounts.check("william", "nope")

    with pytest.raises(TooManyAttempts):
        accounts.check("william", PASSWORD)
    now[0] += WAIT_SECONDS
    assert accounts.check("william", PASSWORD)


def test_a_session_ends_after_30_days(tmp_path):
    now = [1000.0]
    accounts = Accounts(Database(tmp_path / "sok.db"), clock=lambda: now[0])
    token = accounts.open_session()

    assert accounts.session_valid(token)
    now[0] += 31 * 24 * 3600
    assert not accounts.session_valid(token)


def test_the_password_is_hashed(tmp_path, client):
    setup(client)

    data = (tmp_path / "sok.db").read_bytes()

    assert PASSWORD.encode() not in data
    assert b"$argon2" in data


def test_the_account_can_come_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("SOK_USERNAME", "admin")
    monkeypatch.setenv("SOK_PASSWORD", PASSWORD)

    with make_client(tmp_path) as client:
        assert client.get("/api/session").json()["username"] == "admin"
        assert (
            client.post(
                "/api/login", json={"username": "admin", "password": PASSWORD}
            ).status_code
            == 200
        )


def test_the_environment_never_replaces_an_account(tmp_path, monkeypatch):
    with make_client(tmp_path) as client:
        setup(client)
    monkeypatch.setenv("SOK_USERNAME", "admin")
    monkeypatch.setenv("SOK_PASSWORD", PASSWORD)

    with make_client(tmp_path) as client:
        assert client.get("/api/session").json()["username"] == "william"


def test_sok_auth_none_turns_the_login_off(tmp_path, monkeypatch):
    monkeypatch.setenv("SOK_AUTH", "none")

    with make_client(tmp_path) as client:
        assert client.get("/api/session").json()["auth"] == "none"
        assert client.get("/api/private").status_code == 200


def test_the_database_keeps_its_data_when_it_opens_again(tmp_path):
    Accounts(Database(tmp_path / "sok.db")).create("william", PASSWORD)

    db = Database(tmp_path / "sok.db")

    assert db.version == len(MIGRATIONS)
    assert Accounts(db).username() == "william"


def test_the_setup_takes_the_language_of_the_browser(client):
    client.post(
        "/api/setup",
        json={"username": "william", "password": PASSWORD, "language": "fr"},
    )

    assert client.get("/api/session").json()["language"] == "fr"


def test_a_language_s_o_k_lacks_is_ignored(client):
    client.post(
        "/api/setup",
        json={"username": "william", "password": PASSWORD, "language": "xx"},
    )

    assert client.get("/api/session").json()["language"] == "en"


def test_the_texts_need_no_login(client):
    answer = client.get("/api/i18n?lang=de").json()

    assert answer["language"] == "de"
    assert "fr" in answer["languages"]
    assert answer["texts"]["season"] == "Staffel"


def test_the_texts_follow_the_settings_without_a_language(client):
    assert client.get("/api/i18n").json()["language"] == "en"
    assert client.get("/api/i18n?lang=../../etc").json()["language"] == "en"
