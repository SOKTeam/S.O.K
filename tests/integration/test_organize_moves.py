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
from sok.file_operations.base_operations import move_file
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
        monkeypatch.setattr(os, "replace", cross_device_rename)

        report = VideoFileOperations().organize_movies_batch(
            [(source, movie)], str(dest)
        )

        assert report["errors"] == []
        assert report["total_moved"] == 1
        assert not source.exists()
        assert os.path.exists(report["moved"][0]["to"])

    def test_existing_destination_is_backed_up_and_replaced(
        self, tmp_path, config, movie
    ):
        config._values["backup_before_rename"] = True
        source = tmp_path / "matrix.1999.mkv"
        source.write_text("new")
        dest = tmp_path / "library"
        dest.mkdir()
        existing = dest / VideoFileOperations().generate_new_filename(
            movie, source.name
        )
        existing.write_text("old")

        report = VideoFileOperations().organize_movies_batch(
            [(source, movie)], str(dest)
        )

        assert report["errors"] == []
        assert existing.read_text() == "new"
        assert (dest / f"{existing.name}.backup").read_text() == "old"
        assert not source.exists()

    def test_existing_destination_is_replaced_without_backup(
        self, tmp_path, config, movie
    ):
        source = tmp_path / "matrix.1999.mkv"
        source.write_text("new")
        dest = tmp_path / "library"
        dest.mkdir()
        existing = dest / VideoFileOperations().generate_new_filename(
            movie, source.name
        )
        existing.write_text("old")

        report = VideoFileOperations().organize_movies_batch(
            [(source, movie)], str(dest)
        )

        assert report["errors"] == []
        assert existing.read_text() == "new"
        assert not (dest / f"{existing.name}.backup").exists()


class TestMoveFile:
    def test_backup_is_restored_when_move_fails(self, tmp_path):
        destination = tmp_path / "file.mkv"
        destination.write_text("old")
        missing_source = tmp_path / "missing.mkv"

        with pytest.raises(OSError):
            move_file(str(missing_source), str(destination), backup=True)

        assert destination.read_text() == "old"
        assert not (tmp_path / "file.mkv.backup").exists()
