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

from sok.ui.controllers.source_scanner import scan_sources


class FakeOps:
    """Returns files in a shuffled order, like the file system can."""

    def __init__(self, files):
        self._files = files

    def find_files(self, path):
        return [f for f in self._files if f.startswith(path)]


def test_files_are_sorted_naturally_within_each_folder():
    ops = FakeOps(
        [
            "/b/Show S01E10.mkv",
            "/b/Show S01E02.mkv",
            "/a/Movie.mkv",
            "/b/Show S01E1.mkv",
            "/b/show S01E03.mkv",
        ]
    )

    files = scan_sources(ops, [Path("/b"), Path("/a")])

    assert [f.name for f in files] == [
        "Show S01E1.mkv",
        "Show S01E02.mkv",
        "show S01E03.mkv",
        "Show S01E10.mkv",
        "Movie.mkv",
    ]


def test_a_file_found_twice_is_listed_once():
    ops = FakeOps(["/a/x.mkv"])

    assert scan_sources(ops, [Path("/a"), Path("/a")]) == [Path("/a/x.mkv")]


class ExtensionOps(FakeOps):
    supported_extensions = [".mkv"]


def test_files_are_kept_when_their_extension_is_supported(tmp_path):
    episode = tmp_path / "Show S01E01.mkv"
    notes = tmp_path / "notes.txt"
    episode.write_bytes(b"")
    notes.write_bytes(b"")

    assert scan_sources(ExtensionOps([]), [episode, notes]) == [episode]
