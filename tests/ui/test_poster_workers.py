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
from pathlib import Path

import pytest

from sok.ui.workers import batch_worker, organize_worker
from sok.ui.workers.batch_worker import BatchOrganizeWorker
from sok.ui.workers.organize_worker import OrganizeWorker

MOVED = {"moved": [{"from": "/in/a.mkv", "to": "/out/A (2020).mkv"}]}


class FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


class FakeOps:
    def organize_files_list(self, **kwargs):
        return {"total_files": 1, "total_moved": 1, **MOVED}


@pytest.mark.parametrize("enabled", [True, False])
def test_batch_rename_downloads_posters_when_asked(monkeypatch, enabled):
    calls = []
    monkeypatch.setattr(batch_worker, "save_artwork", lambda *a: calls.append(a))
    item = object()
    worker = BatchOrganizeWorker(
        [(Path("/in/a.mkv"), item)],
        "/out",
        lambda **kwargs: {"total_files": 1, "total_moved": 1, **MOVED},
        config=FakeConfig(download_posters=enabled),
    )

    worker.execute()

    assert calls == (
        [([(Path("/in/a.mkv"), item)], MOVED["moved"], "/out")] if enabled else []
    )


@pytest.mark.parametrize("enabled", [True, False])
def test_one_item_rename_downloads_posters_when_asked(monkeypatch, enabled):
    calls = []
    monkeypatch.setattr(organize_worker, "save_artwork", lambda *a: calls.append(a))
    item = object()
    worker = OrganizeWorker(
        [Path("/in/a.mkv")],
        Path("/out"),
        item,
        FakeOps(),
        config=FakeConfig(download_posters=enabled),
    )

    worker.execute()

    assert len(calls) == (1 if enabled else 0)
    if enabled:
        assert calls[0] == ([(Path("/in/a.mkv"), item)], MOVED["moved"], "/out")
