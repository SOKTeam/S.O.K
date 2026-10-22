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
from fastapi.testclient import TestClient

from sok.server.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>S.O.K</title>")
    (dist / "assets" / "app-1a2b.js").write_text("console.log('sok')")
    (tmp_path / "secret.txt").write_text("not served")
    monkeypatch.setenv("SOK_WEB_DIR", str(dist))
    with TestClient(create_app(tmp_path / "config")) as client:
        yield client


def test_the_pages_answer_the_interface(client):
    for path in ("/", "/movies", "/settings/keys"):
        answer = client.get(path)
        assert answer.status_code == 200
        assert "<title>S.O.K</title>" in answer.text
        assert answer.headers["cache-control"] == "no-cache"


def test_the_assets_are_kept_by_the_browser(client):
    answer = client.get("/assets/app-1a2b.js")

    assert answer.text == "console.log('sok')"
    assert "immutable" in answer.headers["cache-control"]


def test_the_api_keeps_its_answers(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/nope").status_code == 404
    assert client.get("/api/nope").json()["detail"] == "not_found"


def test_no_file_outside_the_build(client):
    answer = client.get("/..%2Fsecret.txt")

    assert "not served" not in answer.text


def test_without_a_build_only_the_api(tmp_path, monkeypatch):
    monkeypatch.setenv("SOK_WEB_DIR", str(tmp_path / "none"))
    with TestClient(create_app(tmp_path / "config")) as client:
        assert client.get("/").status_code == 404
        assert client.get("/api/health").status_code == 200
