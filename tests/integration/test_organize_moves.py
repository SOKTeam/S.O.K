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
import errno
import os

import pytest

from sok.core.media_manager import UniversalMediaManager
from sok.file_operations import video_operations
from sok.file_operations.video_operations import VideoFileOperations
from sok.media.video.movie import Movie


class FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


@pytest.fixture
def config(monkeypatch):
    cfg = FakeConfig(skip_duplicates=False, backup_before_rename=False)
    monkeypatch.setattr(video_operations, "get_config_manager", lambda: cfg)
    return cfg


@pytest.fixture
def movie():
    item = Movie("The Matrix", "en", UniversalMediaManager())
    item.year = 1999
    return item


class TestOrganizeMoves:
    def test_move_across_devices(self, tmp_path, monkeypatch, config, movie):
        """Moving to another volume must fall back to copy + delete."""
        source = tmp_path / "downloads" / "matrix.1999.mkv"
        source.parent.mkdir()
        source.write_text("video")
        dest = tmp_path / "library"
        dest.mkdir()

        def cross_device_rename(src, dst):
            raise OSError(errno.EXDEV, "Invalid cross-device link")

        monkeypatch.setattr(os, "rename", cross_device_rename)

        report = VideoFileOperations().organize_movies_batch(
            [(source, movie)], str(dest)
        )

        assert report["errors"] == []
        assert report["total_moved"] == 1
        assert not source.exists()
        assert os.path.exists(report["moved"][0]["to"])
