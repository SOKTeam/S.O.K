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

from sok.core.history import record
from sok.core.media_manager import UniversalMediaManager
from sok.file_operations import video_operations
from sok.file_operations.subtitles import find_subtitles
from sok.file_operations.video_operations import VideoFileOperations
from sok.media.video.movie import Movie

VIDEOS = (".mkv", ".mp4")


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
def dune():
    item = Movie("Dune", "en", UniversalMediaManager())
    item.year = 2021
    return item


def touch(folder, *names):
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder / name).write_text(name)


def rename_dune(tmp_path, dune):
    """Rename in/dune.2021.mkv to out/ inside record(); return report, journal."""
    (tmp_path / "out").mkdir(exist_ok=True)
    with record("movie") as journal:
        report = VideoFileOperations().organize_movies_batch(
            [(tmp_path / "in/dune.2021.mkv", dune)], str(tmp_path / "out")
        )
    return report, journal


def test_subtitles_are_found_with_their_suffix(tmp_path):
    touch(
        tmp_path,
        "Movie.mkv",
        "Movie.srt",
        "Movie.fr.srt",
        "Movie.en.forced.ass",
        "Movie.nfo",
        "Moviegoer.srt",
        "Other.srt",
    )

    found = find_subtitles(tmp_path / "Movie.mkv", VIDEOS)

    assert [suffix for _, suffix in found] == [".en.forced.ass", ".fr.srt", ".srt"]


def test_the_longest_video_name_wins(tmp_path):
    touch(tmp_path, "Movie.mkv", "Movie.Part2.mkv", "Movie.srt", "Movie.Part2.srt")

    assert [p.name for p, _ in find_subtitles(tmp_path / "Movie.mkv", VIDEOS)] == [
        "Movie.srt"
    ]
    assert [
        p.name for p, _ in find_subtitles(tmp_path / "Movie.Part2.mkv", VIDEOS)
    ] == ["Movie.Part2.srt"]


def test_the_extension_case_does_not_matter(tmp_path):
    touch(tmp_path, "Movie.mkv", "Movie.FR.SRT")

    assert find_subtitles(tmp_path / "Movie.mkv", VIDEOS)[0][1] == ".FR.SRT"


def test_subtitles_follow_the_renamed_movie(tmp_path, config, dune, rename_history):
    touch(tmp_path / "in", "dune.2021.mkv", "dune.2021.fr.srt", "dune.2021.nfo")

    report, _ = rename_dune(tmp_path, dune)

    assert report["total_moved"] == 1
    assert len(report["subtitles"]) == 1
    assert (tmp_path / "out/Dune (2021).mkv").exists()
    assert (tmp_path / "out/Dune (2021).fr.srt").read_text() == "dune.2021.fr.srt"
    assert (tmp_path / "in/dune.2021.nfo").exists()


def test_the_setting_turns_it_off(tmp_path, config, dune, rename_history):
    config._values["subtitles_follow_video"] = False
    touch(tmp_path / "in", "dune.2021.mkv", "dune.2021.srt")

    report, _ = rename_dune(tmp_path, dune)

    assert report.get("subtitles", []) == []
    assert (tmp_path / "in/dune.2021.srt").exists()


def test_an_existing_subtitle_is_skipped_with_skip_duplicates(
    tmp_path, config, dune, rename_history
):
    config._values["skip_duplicates"] = True
    touch(tmp_path / "in", "dune.2021.mkv", "dune.2021.srt")
    touch(tmp_path / "out", "Dune (2021).srt")

    report, _ = rename_dune(tmp_path, dune)

    assert report["total_moved"] == 1
    assert [s["file"] for s in report["skipped"]] == [
        str(tmp_path / "in/dune.2021.srt")
    ]
    assert (tmp_path / "out/Dune (2021).srt").read_text() == "Dune (2021).srt"


def test_undoing_the_video_puts_its_subtitles_back(
    tmp_path, config, dune, rename_history
):
    touch(tmp_path / "in", "dune.2021.mkv", "dune.2021.srt", "dune.2021.en.srt")
    _, journal = rename_dune(tmp_path, dune)
    operation = rename_history.get(journal.operation_id)
    assert [m.follows for m in operation.moves] == [
        None,
        str(tmp_path / "out/Dune (2021).mkv"),
        str(tmp_path / "out/Dune (2021).mkv"),
    ]

    report = rename_history.undo(journal.operation_id, 0)

    assert len(report.restored) == 3
    assert sorted(p.name for p in (tmp_path / "in").iterdir()) == [
        "dune.2021.en.srt",
        "dune.2021.mkv",
        "dune.2021.srt",
    ]


def test_a_subtitle_can_be_put_back_alone(tmp_path, config, dune, rename_history):
    touch(tmp_path / "in", "dune.2021.mkv", "dune.2021.srt")
    _, journal = rename_dune(tmp_path, dune)

    rename_history.undo(journal.operation_id, 1)

    assert (tmp_path / "in/dune.2021.srt").exists()
    assert (tmp_path / "out/Dune (2021).mkv").exists()
