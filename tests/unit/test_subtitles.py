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
from sok.file_operations.subtitles import (
    find_subs_folder,
    find_subtitles,
    plan_subtitles,
)
from sok.file_operations.video_operations import VideoFileOperations
from sok.media.video.movie import Movie
from test_subtitle_language import write_srt

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


def planned(tmp_path, video="Movie.mkv", new="out/Dune (2021).mkv"):
    """The plan of a video, as names relative to tmp_path."""
    plan = plan_subtitles(tmp_path / video, str(tmp_path / new), VIDEOS)
    return {
        str(source)[len(str(tmp_path)) + 1 :]: target[len(str(tmp_path)) + 1 :]
        for source, target in plan
    }


def test_the_language_of_the_text_is_added_when_the_name_lacks_it(tmp_path):
    touch(tmp_path, "Movie.mkv")
    write_srt(tmp_path / "Movie.srt", "fr")
    write_srt(tmp_path / "Movie.forced.srt", "en")

    assert planned(tmp_path) == {
        "Movie.forced.srt": "out/Dune (2021).en.forced.srt",
        "Movie.srt": "out/Dune (2021).fr.srt",
    }


def test_a_language_in_the_name_is_kept_as_it_is(tmp_path):
    touch(tmp_path, "Movie.mkv")
    write_srt(tmp_path / "Movie.English.srt", "fr")

    assert planned(tmp_path) == {"Movie.English.srt": "out/Dune (2021).English.srt"}


def test_an_unsure_subtitle_keeps_its_name(tmp_path):
    touch(tmp_path, "Movie.mkv", "Movie.srt")

    assert planned(tmp_path) == {"Movie.srt": "out/Dune (2021).srt"}


def test_a_guessed_language_never_takes_the_name_of_another_subtitle(tmp_path):
    touch(tmp_path, "Movie.mkv")
    write_srt(tmp_path / "Movie.srt", "fr")
    write_srt(tmp_path / "Movie.fr.srt", "fr")

    assert planned(tmp_path) == {
        "Movie.fr.srt": "out/Dune (2021).fr.srt",
        "Movie.srt": "out/Dune (2021).srt",
    }


def test_a_vobsub_pair_keeps_one_name(tmp_path):
    touch(tmp_path, "Movie.mkv")
    (tmp_path / "Movie.idx").write_text("id: de, index: 0\n")
    (tmp_path / "Movie.sub").write_bytes(b"\x00\x00\x01\xba" * 100)

    assert planned(tmp_path) == {
        "Movie.idx": "out/Dune (2021).de.idx",
        "Movie.sub": "out/Dune (2021).de.sub",
    }


def test_the_subs_folder_of_a_movie(tmp_path):
    touch(tmp_path, "Movie.mkv")
    touch(
        tmp_path / "Subs",
        "2_English.srt",
        "3_English.srt",
        "4_English_SDH.srt",
        "10_French.srt",
        "notes.txt",
    )

    assert planned(tmp_path) == {
        "Subs/2_English.srt": "out/Dune (2021).en.srt",
        "Subs/3_English.srt": "out/Dune (2021).en.2.srt",
        "Subs/4_English_SDH.srt": "out/Dune (2021).en.sdh.srt",
        "Subs/10_French.srt": "out/Dune (2021).fr.srt",
    }


def test_a_subs_name_without_language_is_read_from_its_text(tmp_path):
    touch(tmp_path, "Movie.mkv")
    (tmp_path / "subs").mkdir()
    write_srt(tmp_path / "subs/track3.srt", "es")

    assert planned(tmp_path) == {"subs/track3.srt": "out/Dune (2021).es.srt"}


def test_the_subs_folder_numbers_after_the_subtitles_beside(tmp_path):
    touch(tmp_path, "Movie.mkv", "Movie.en.srt")
    touch(tmp_path / "Subs", "2_English.srt")

    assert planned(tmp_path)["Subs/2_English.srt"] == "out/Dune (2021).en.2.srt"


def test_the_subs_folder_of_an_episode_of_a_pack(tmp_path):
    touch(tmp_path, "Show.S01E01.mkv", "Show.S01E02.mkv")
    touch(tmp_path / "Subs/Show.S01E01", "2_English.srt")
    touch(tmp_path / "Subs/Show.S01E02", "2_English.srt")
    touch(tmp_path / "Subs", "loose.srt")

    assert find_subs_folder(tmp_path / "Show.S01E02.mkv", VIDEOS) == [
        tmp_path / "Subs/Show.S01E02/2_English.srt"
    ]


def test_loose_subs_of_a_pack_belong_to_no_episode(tmp_path):
    touch(tmp_path, "Show.S01E01.mkv", "Show.S01E02.mkv")
    touch(tmp_path / "Subs", "2_English.srt")

    assert find_subs_folder(tmp_path / "Show.S01E01.mkv", VIDEOS) == []


def test_subs_follow_the_movie_and_go_back_with_it(
    tmp_path, config, dune, rename_history
):
    touch(tmp_path / "in", "dune.2021.mkv")
    touch(tmp_path / "in/Subs", "2_English.srt", "3_French.srt")

    report, journal = rename_dune(tmp_path, dune)

    assert len(report["subtitles"]) == 2
    assert (tmp_path / "out/Dune (2021).en.srt").read_text() == "2_English.srt"
    assert (tmp_path / "out/Dune (2021).fr.srt").read_text() == "3_French.srt"

    rename_history.undo(journal.operation_id, 0)

    assert sorted(p.name for p in (tmp_path / "in/Subs").iterdir()) == [
        "2_English.srt",
        "3_French.srt",
    ]
