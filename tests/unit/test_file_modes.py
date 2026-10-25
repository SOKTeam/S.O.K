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

from sok.core.history import COPY, LINK, MOVE, OCCUPIED, Operation, record
from sok.core.media_manager import UniversalMediaManager
from sok.file_operations import base_operations, video_operations
from sok.file_operations.base_operations import HardLinkError, can_hard_link, move_file
from sok.file_operations.video_operations import VideoFileOperations
from sok.media.video.movie import Movie
from sok.ui.controllers.file_mode import link_problem


class FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def no_links(monkeypatch):
    def cross_device(src, dst):
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(base_operations.os, "link", cross_device)


@pytest.fixture
def files(tmp_path):
    source = tmp_path / "downloads" / "dune.mkv"
    source.parent.mkdir()
    source.write_text("video")
    library = tmp_path / "library"
    library.mkdir()
    return source, library / "Dune (2021).mkv"


def rename(source, target, mode, **kwargs):
    with record("movie") as journal:
        move_file(str(source), str(target), mode=mode, **kwargs)
    return journal


def test_a_hard_link_leaves_the_source_in_place(files, rename_history):
    source, target = files

    journal = rename(source, target, LINK)

    assert source.exists()
    assert os.path.samefile(source, target)
    assert rename_history.get(journal.operation_id).moves[0].mode == LINK


def test_a_copy_leaves_the_source_in_place(files, rename_history):
    source, target = files

    rename(source, target, COPY)

    assert source.read_text() == target.read_text() == "video"
    assert not os.path.samefile(source, target)


def test_a_failed_link_is_an_error_never_a_copy(files, monkeypatch, rename_history):
    source, target = files
    target.write_text("old")
    no_links(monkeypatch)

    with pytest.raises(HardLinkError):
        rename(source, target, LINK, backup=True)

    assert target.read_text() == "old"
    assert sorted(p.name for p in target.parent.iterdir()) == [target.name]
    assert rename_history.operations() == []


def test_linking_a_file_onto_itself_does_nothing(files, rename_history):
    source, _ = files

    journal = rename(source, source, LINK)

    assert source.read_text() == "video"
    assert journal.operation_id is None


def test_undoing_a_link_deletes_it(files, rename_history):
    source, target = files
    journal = rename(source, target, LINK)

    report = rename_history.undo(journal.operation_id)

    assert len(report.restored) == 1
    assert source.read_text() == "video"
    assert not target.exists()


def test_undoing_a_link_whose_source_is_gone_puts_it_back(files, rename_history):
    source, target = files
    journal = rename(source, target, LINK)
    source.unlink()

    rename_history.undo(journal.operation_id)

    assert source.read_text() == "video"
    assert not target.exists()


def test_a_link_whose_source_was_replaced_stays(files, rename_history):
    source, target = files
    journal = rename(source, target, LINK)
    source.unlink()
    source.write_text("another file")

    report = rename_history.undo(journal.operation_id)

    assert report.skipped[0][1] == OCCUPIED
    assert target.read_text() == "video"


def test_undoing_a_copy_deletes_it_when_the_source_is_the_same(files, rename_history):
    source, target = files
    journal = rename(source, target, COPY)

    rename_history.undo(journal.operation_id)

    assert source.exists()
    assert not target.exists()


def test_a_copy_whose_source_changed_stays(files, rename_history):
    source, target = files
    journal = rename(source, target, COPY)
    source.write_text("a longer video")

    report = rename_history.undo(journal.operation_id)

    assert report.skipped[0][1] == OCCUPIED
    assert target.exists()


def test_an_old_history_is_made_of_moves():
    operation = Operation.from_dict(
        {
            "id": "a",
            "date": "2026-10-21T15:42:00",
            "moves": [{"source": "/in/a.mkv", "target": "/out/A.mkv"}],
        }
    )

    assert operation.moves[0].mode == MOVE


def test_the_link_test(files, monkeypatch):
    source, target = files

    assert can_hard_link(str(source), str(target.parent))
    assert list(target.parent.iterdir()) == []
    no_links(monkeypatch)
    assert not can_hard_link(str(source), str(target.parent))
    assert link_problem([source], str(target.parent)) == source.parent


def test_movies_and_their_subtitles_are_linked(tmp_path, monkeypatch, rename_history):
    cfg = FakeConfig(file_mode=LINK)
    monkeypatch.setattr(video_operations, "get_config_manager", lambda: cfg)
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    (downloads / "dune.2021.mkv").write_text("video")
    (downloads / "dune.2021.fr.srt").write_text("subtitle")
    library = tmp_path / "library"
    library.mkdir()
    movie = Movie("Dune", "en", UniversalMediaManager())
    movie.year = 2021

    VideoFileOperations().organize_movies_batch(
        [(downloads / "dune.2021.mkv", movie)], str(library)
    )

    assert os.path.samefile(downloads / "dune.2021.mkv", library / "Dune (2021).mkv")
    assert os.path.samefile(
        downloads / "dune.2021.fr.srt", library / "Dune (2021).fr.srt"
    )
