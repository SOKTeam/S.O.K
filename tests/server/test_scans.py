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
import time

import pytest
from fastapi.testclient import TestClient

from sok.server.app import create_app
from sok.server.db import Database
from sok.server.scans import INTERRUPTED


@pytest.fixture
def downloads(tmp_path):
    folder = tmp_path / "downloads"
    files = [
        "Dune.2021.1080p.mkv",
        "The.Matrix.1999.mkv",
        "Severance/Season 1/Severance.S01E01.mkv",
        "Severance/Season 1/Severance.S01E02.mkv",
        "Frank Herbert - Dune.epub",
        "Chrono Trigger (USA).smc",
        "Mystery.iso",
        "notes.txt",
    ]
    for name in files:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name)
    return folder


@pytest.fixture
def client(tmp_path, downloads):
    with TestClient(create_app(tmp_path)) as client:
        client.post(
            "/api/setup", json={"username": "william", "password": "correct horse"}
        )
        client.patch("/api/settings", json={"folders": {"sources": [str(downloads)]}})
        yield client


def scan(client):
    """Run an analysis and return its summary once it is over."""
    assert client.post("/api/scans").status_code == 202
    for _ in range(200):
        summary = client.get("/api/scans/current").json()
        if summary["scan"]["status"] != "running":
            return summary
        time.sleep(0.02)
    raise AssertionError("the analysis did not end")


def rows(tmp_path):
    db = Database(tmp_path / "sok.db")
    with db.transaction() as conn:
        result = {row["key"]: dict(row) for row in conn.execute("SELECT * FROM rows")}
    db.close()
    return result


def test_before_any_analysis(client):
    summary = client.get("/api/scans/current").json()

    assert summary["scan"] is None
    assert summary["counts"]["movies"]["total"] == 0


def test_an_analysis_sorts_the_files_into_rows(client, tmp_path, downloads):
    summary = scan(client)

    assert summary["scan"]["status"] == "done"
    counts = {media: c["total"] for media, c in summary["counts"].items()}
    assert counts == {"movies": 2, "tv": 1, "music": 0, "books": 1, "games": 1}
    # Every row is searched.
    assert summary["counts"]["movies"]["ok"] == 2
    assert summary["counts"]["tv"]["ok"] == 1
    assert summary["counts"]["books"]["ok"] == 1
    series = next(r for r in rows(tmp_path).values() if r["media_type"] == "tv")
    assert series["title"] == "Severance"
    assert [f.rsplit("/", 1)[1] for f in json.loads(series["files"])] == [
        "Severance.S01E01.mkv",
        "Severance.S01E02.mkv",
    ]
    assert [c["path"] for c in summary["to_check"]] == [str(downloads / "Mystery.iso")]
    assert summary["to_check"][0]["media_type"] == "games"


def test_a_new_analysis_keeps_the_choices(client, tmp_path, downloads):
    scan(client)
    db = Database(tmp_path / "sok.db")
    with db.transaction() as conn:
        conn.execute(
            "UPDATE rows SET query = 'Dune', selected = 1, status = 'ok'"
            " WHERE kind = 'movie' AND files LIKE '%Dune%'"
        )
        conn.execute("UPDATE rows SET query = 'Severance' WHERE kind = 'episode'")
    db.close()
    (downloads / "The.Matrix.1999.mkv").unlink()
    (downloads / "Severance/Season 1/Severance.S01E03.mkv").write_text("3")

    summary = scan(client)

    current = rows(tmp_path)
    assert summary["counts"]["movies"]["total"] == 1
    dune = next(r for r in current.values() if r["kind"] == "movie")
    assert (dune["query"], dune["selected"], dune["status"]) == ("Dune", 1, "ok")
    series = next(r for r in current.values() if r["kind"] == "episode")
    assert series["query"] == "Severance"
    assert len(json.loads(series["files"])) == 3


def test_a_file_to_check_gets_the_type_chosen(client, downloads):
    scan(client)

    summary = client.post(
        "/api/to-check", json={"path": str(downloads / "Mystery.iso"), "kind": "movie"}
    ).json()

    assert summary["to_check"] == []
    assert summary["counts"]["movies"]["total"] == 3
    # The next analyses remember it.
    assert scan(client)["counts"]["movies"]["total"] == 3


def test_a_confirmed_file_is_searched(client, downloads, tmp_path, media_manager):
    scan(client)
    media_manager.searches.clear()

    client.post(
        "/api/to-check", json={"path": str(downloads / "Mystery.iso"), "kind": "movie"}
    )

    mystery = next(r for r in rows(tmp_path).values() if "Mystery.iso" in r["files"])
    assert media_manager.searches == ["Mystery"]
    assert mystery["status"] == "missing"


def test_a_confirmed_file_keeps_its_type_when_the_search_stops(
    client, downloads, tmp_path, media_manager
):
    scan(client)
    media_manager.apis = []

    answer = client.post(
        "/api/to-check", json={"path": str(downloads / "Mystery.iso"), "kind": "movie"}
    )

    assert answer.status_code == 200
    summary = answer.json()
    assert summary["search_error"] == {"code": "missing_key", "service": "tmdb"}
    assert summary["to_check"] == []
    mystery = next(r for r in rows(tmp_path).values() if "Mystery.iso" in r["files"])
    assert mystery["status"] == "pending"


def test_wrong_type_choices(client, downloads):
    scan(client)

    assert (
        client.post(
            "/api/to-check", json={"path": str(downloads / "x.iso"), "kind": "movie"}
        ).json()["detail"]
        == "unknown_file"
    )
    assert (
        client.post(
            "/api/to-check",
            json={"path": str(downloads / "Mystery.iso"), "kind": "anime"},
        ).json()["detail"]
        == "invalid_kind"
    )


def test_no_source_folder(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        client.post(
            "/api/setup", json={"username": "william", "password": "correct horse"}
        )

        answer = client.post("/api/scans")

    assert answer.status_code == 409
    assert answer.json()["detail"] == "no_sources"


def test_a_missing_source_is_reported(client, tmp_path, downloads):
    gone = tmp_path / "gone"
    gone.mkdir()
    client.patch(
        "/api/settings", json={"folders": {"sources": [str(downloads), str(gone)]}}
    )
    gone.rmdir()

    summary = scan(client)

    assert summary["scan"]["status"] == "done"
    assert summary["scan"]["missing_sources"] == [str(gone)]


def test_the_analyses_need_a_login(client):
    client.post("/api/logout")

    assert client.post("/api/scans").status_code == 401
    assert client.get("/api/scans/current").status_code == 401
    assert client.get("/api/events").status_code == 401


def test_an_analysis_cut_by_a_restart_is_interrupted(tmp_path):
    db = Database(tmp_path / "sok.db")
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO scans (started, status) VALUES ('2026-10-21', 'running')"
        )
    db.close()

    with TestClient(create_app(tmp_path)) as client:
        client.post(
            "/api/setup", json={"username": "william", "password": "correct horse"}
        )
        summary = client.get("/api/scans/current").json()

    assert summary["scan"]["status"] == INTERRUPTED


def test_the_events_start_with_the_state_of_the_analysis(client):
    scan(client)

    with client.stream("GET", "/api/events") as stream:
        assert stream.headers["content-type"].startswith("text/event-stream")
        lines = stream.iter_lines()
        assert next(lines) == "event: scan"
        data = json.loads(next(lines).removeprefix("data: "))

    assert data["type"] == "scan"
    assert data["scan"]["status"] == "done"
