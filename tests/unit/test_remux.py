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
"""The conversion of the videos to MKV while renaming them (remux.py)."""

import pytest

from sok.core.history import COPY, LINK, MOVE, OCCUPIED, record
from sok.file_operations import remux, video_operations
from sok.file_operations.remux import RemuxError, convert_to_mkv, mkv_name
from sok.file_operations.video_operations import VideoFileOperations
from sok.media.video.movie import Movie


@pytest.fixture
def video(tmp_path):
    source = tmp_path / "downloads" / "Dune.2021.1080p.mp4"
    source.parent.mkdir()
    source.write_bytes(b"x" * 1000)
    (tmp_path / "movies").mkdir()
    return source


def test_the_formats_converted_get_mkv():
    assert mkv_name("Dune (2021).mp4") == "Dune (2021).mkv"
    for name in ("a.M4V", "a.mov", "a.ts"):
        assert mkv_name(name) == "a.mkv"
    # AVI is never converted: its sound often goes out of sync.
    for name in ("a.avi", "a.mkv", "a.webm"):
        assert mkv_name(name) == name


def test_without_mkvmerge_nothing_is_converted(video, tmp_path, monkeypatch):
    monkeypatch.delenv("SOK_MKVMERGE", raising=False)
    monkeypatch.setattr(remux.shutil, "which", lambda name: None)
    target = tmp_path / "movies" / "Dune (2021).mkv"

    with pytest.raises(RemuxError, match="not installed"):
        convert_to_mkv(str(video), str(target))
    assert video.exists() and not target.exists()


def test_a_move_deletes_the_original_once_checked(
    fake_mkvmerge, video, tmp_path, rename_history
):
    target = tmp_path / "movies" / "Dune (2021).mkv"

    with record("movie") as journal:
        convert_to_mkv(str(video), str(target), mode=MOVE)

    assert target.read_bytes() == b"x" * 1000
    assert not video.exists()
    # No temporary file left.
    assert [p.name for p in target.parent.iterdir()] == [target.name]
    move = rename_history.get(journal.operation_id).moves[0]
    assert (move.source, move.target, move.mode, move.converted) == (
        str(video),
        str(target),
        MOVE,
        True,
    )


def test_a_copy_keeps_the_original(fake_mkvmerge, video, tmp_path):
    target = tmp_path / "movies" / "Dune (2021).mkv"

    convert_to_mkv(str(video), str(target), mode=COPY)

    assert video.exists() and target.exists()


def test_a_hard_link_is_never_converted(fake_mkvmerge, video, tmp_path):
    with pytest.raises(ValueError):
        convert_to_mkv(str(video), str(tmp_path / "movies" / "a.mkv"), mode=LINK)


@pytest.mark.parametrize(
    "problem, message",
    [
        ("fail", "could not be read"),
        ("tracks", "same tracks"),
        ("duration", "same duration"),
    ],
)
def test_a_conversion_not_right_leaves_everything_as_it_was(
    fake_mkvmerge, video, tmp_path, problem, message
):
    if problem == "fail":
        fake_mkvmerge.fail = True
    elif problem == "tracks":
        fake_mkvmerge.tracks = ["video"]
    else:
        fake_mkvmerge.duration = 40_000_000_000
    target = tmp_path / "movies" / "Dune (2021).mkv"

    with pytest.raises(RemuxError, match=message):
        convert_to_mkv(str(video), str(target), mode=MOVE)

    assert video.read_bytes() == b"x" * 1000
    assert list(target.parent.iterdir()) == []


def test_a_file_already_there_is_kept_as_backup(fake_mkvmerge, video, tmp_path):
    target = tmp_path / "movies" / "Dune (2021).mkv"
    target.write_text("old")

    backup = convert_to_mkv(str(video), str(target), backup=True)

    assert backup == f"{target}.backup"
    assert (tmp_path / "movies" / "Dune (2021).mkv.backup").read_text() == "old"


class FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def movie_batch(video, tmp_path, mode, monkeypatch, to_mkv=True):
    config = FakeConfig(file_mode=mode, subtitles_follow_video=False)
    monkeypatch.setattr(video_operations, "get_config_manager", lambda: config)
    movie = Movie("Dune", "en", None)
    movie.title = "Dune"
    movie.year = 2021
    return VideoFileOperations().organize_movies_batch(
        [(video, movie)], str(tmp_path / "movies"), to_mkv=to_mkv
    )


def test_the_movie_batch_converts_and_names_it_mkv(
    fake_mkvmerge, video, tmp_path, monkeypatch
):
    report = movie_batch(video, tmp_path, MOVE, monkeypatch)

    assert report["moved"] == [
        {"from": str(video), "to": str(tmp_path / "movies" / "Dune (2021).mkv")}
    ]
    assert fake_mkvmerge.conversions


def test_the_movie_batch_does_not_convert_hard_links(
    fake_mkvmerge, video, tmp_path, monkeypatch
):
    report = movie_batch(video, tmp_path, LINK, monkeypatch)

    assert report["moved"][0]["to"].endswith("Dune (2021).mp4")
    assert not fake_mkvmerge.conversions


def test_a_failed_conversion_is_an_error_of_the_file(
    fake_mkvmerge, video, tmp_path, monkeypatch
):
    fake_mkvmerge.fail = True

    report = movie_batch(video, tmp_path, MOVE, monkeypatch)

    assert report["moved"] == []
    assert report["errors"][0]["file"] == str(video)
    assert "MKV conversion failed" in report["errors"][0]["error"]
    assert video.exists()


def test_undo_of_a_move_puts_the_mkv_back_with_the_old_name(
    fake_mkvmerge, video, tmp_path, rename_history
):
    target = tmp_path / "movies" / "Dune (2021).mkv"
    with record("movie") as journal:
        convert_to_mkv(str(video), str(target), mode=MOVE)

    report = rename_history.undo(journal.operation_id)

    back = video.with_suffix(".mkv")
    assert len(report.restored) == 1
    assert back.exists() and not target.exists() and not video.exists()


def test_undo_of_a_copy_deletes_the_mkv(fake_mkvmerge, video, tmp_path, rename_history):
    target = tmp_path / "movies" / "Dune (2021).mkv"
    with record("movie") as journal:
        convert_to_mkv(str(video), str(target), mode=COPY)

    rename_history.undo(journal.operation_id)

    assert video.exists() and not target.exists()
    assert not video.with_suffix(".mkv").exists()


def test_undo_does_not_replace_a_file_at_the_old_place(
    fake_mkvmerge, video, tmp_path, rename_history
):
    target = tmp_path / "movies" / "Dune (2021).mkv"
    with record("movie") as journal:
        convert_to_mkv(str(video), str(target), mode=MOVE)
    video.with_suffix(".mkv").write_text("another")

    report = rename_history.undo(journal.operation_id)

    assert report.skipped[0][1] == OCCUPIED
    assert target.exists()


def test_a_move_whose_duration_cannot_be_read_is_refused(
    fake_mkvmerge, video, tmp_path
):
    fake_mkvmerge.source_duration = None
    target = tmp_path / "movies" / "Dune (2021).mkv"

    with pytest.raises(RemuxError, match="duration of the original"):
        convert_to_mkv(str(video), str(target), mode=MOVE)
    assert video.exists() and list(target.parent.iterdir()) == []

    # A copy keeps the original: the other checks are enough.
    convert_to_mkv(str(video), str(target), mode=COPY)
    assert target.exists()


def pes_packet(pid, pts, stream_id=0xE0):
    """A TS packet that starts a PES packet with this PTS (90 kHz)."""
    stamp = bytes(
        [
            0x21 | ((pts >> 29) & 0x0E),
            (pts >> 22) & 0xFF,
            0x01 | ((pts >> 14) & 0xFE),
            (pts >> 7) & 0xFF,
            0x01 | ((pts << 1) & 0xFE),
        ]
    )
    pes = b"\x00\x00\x01" + bytes([stream_id, 0, 0, 0x80, 0x80, 5]) + stamp
    header = bytes([0x47, 0x40 | (pid >> 8), pid & 0xFF, 0x10])
    return (header + pes).ljust(188, b"\xff")


def filler(count):
    return (bytes([0x47, 0x1F, 0xFF, 0x10])).ljust(188, b"\xff") * count


@pytest.mark.parametrize("timecode", [False, True])
def test_the_duration_of_a_ts_is_read_from_its_timestamps(tmp_path, timecode):
    packets = [
        pes_packet(0x100, 900_000),
        pes_packet(0x101, 900_000, stream_id=0xC0),
        *[filler(1)] * 40,
        # 90 s later.
        pes_packet(0x100, 900_000 + 90 * 90_000),
        pes_packet(0x101, 900_000 + 89 * 90_000, stream_id=0xC0),
    ]
    if timecode:
        # M2TS-like packets of 192 bytes.
        packets = [b"\0\0\0\0" + packet for packet in packets]
    path = tmp_path / "video.ts"
    path.write_bytes(b"".join(packets))

    assert remux.source_duration(str(path)) == 90_000_000_000


def test_the_duration_of_a_ts_that_wraps_its_clock(tmp_path):
    start = (1 << 33) - 10 * 90_000
    path = tmp_path / "video.ts"
    path.write_bytes(
        pes_packet(0x100, start) + filler(10) + pes_packet(0x100, 20 * 90_000)
    )

    assert remux.source_duration(str(path)) == 30_000_000_000


def test_no_duration_for_a_file_that_is_not_a_video(tmp_path):
    for name in ("noise.ts", "noise.mp4"):
        path = tmp_path / name
        path.write_bytes(b"not a video" * 100)
        assert remux.source_duration(str(path)) is None
