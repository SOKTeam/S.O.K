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

from sok.core import batch
from sok.core.batch import (
    STATUS_AMBIGUOUS,
    STATUS_READY,
    author_matches,
    evaluate,
    parse_album,
    same_album,
)
from sok.file_operations.music_operations import MusicFileOperations


@pytest.fixture
def tags(monkeypatch):
    """Tags of the files, by file name."""
    values = {}
    monkeypatch.setattr(
        MusicFileOperations,
        "read_metadata",
        lambda self, path: values.get(Path(path).name, {}),
    )
    return values


def test_the_tags_most_tracks_give(tags):
    tags["01.mp3"] = {"album": "Discovery", "artist": "Daft Punk", "year": 2001}
    tags["02.mp3"] = {
        "album": "Discovery",
        "artist": "Daft Punk feat. Romanthony",
        "album_artist": "Daft Punk",
        "year": 2001,
    }
    tags["03.mp3"] = {"album": "Discovery (Bonus)", "artist": "Daft Punk"}

    parsed = parse_album([Path(f"/m/x/{n}") for n in ("01.mp3", "02.mp3", "03.mp3")])

    assert (parsed.query, parsed.title, parsed.author, parsed.year) == (
        "Discovery Daft Punk",
        "Discovery",
        "Daft Punk",
        2001,
    )


@pytest.mark.parametrize(
    "folder, album, artist, year",
    [
        ("Daft Punk - Discovery (2001)", "Discovery", "Daft Punk", 2001),
        ("Radiohead - 1997 - OK Computer", "OK Computer", "Radiohead", 1997),
        ("Radiohead - OK Computer [1997]/CD1", "OK Computer", "Radiohead", 1997),
        ("Discovery", "Discovery", None, None),
    ],
)
def test_without_tags_the_folder_names_the_album(tags, folder, album, artist, year):
    parsed = parse_album([Path(f"/music/{folder}/01 - Track.mp3")])

    assert (parsed.title, parsed.author, parsed.year) == (album, artist, year)


def test_a_year_the_results_do_not_give_is_left_out():
    candidates = [{"title": "Discovery", "artist": "Daft Punk"}]

    assert evaluate("Discovery", 2001, candidates, "Daft Punk", same_album) == (
        0,
        STATUS_READY,
    )


def test_a_year_the_results_give_still_counts():
    candidates = [
        {"title": "Dune", "release_date": "1984-12-14"},
        {"title": "Dune", "release_date": "2021-09-15"},
    ]

    assert evaluate("Dune", 2021, candidates) == (1, STATUS_READY)


def test_two_versions_of_one_album_are_one_album():
    candidates = [
        {"title": "Discovery", "artist": "Daft Punk"},
        {"title": "Discovery", "artist": "Daft Punk"},
        {"title": "Discovery", "artist": "Data Punk"},
    ]

    assert evaluate("Discovery", None, candidates, "Daft Punk", same_album) == (
        0,
        STATUS_READY,
    )
    assert evaluate("Discovery", None, candidates, None, same_album)[1] == (
        STATUS_AMBIGUOUS
    )


@pytest.mark.parametrize(
    "author, candidate, expected",
    [
        ("Herbert", "Frank Herbert", True),
        ("F. Herbert", "Frank Herbert", True),
        ("Frank Herbert", "Frank Herbert", True),
        ("J.R.R. Tolkien", "J. R. R. Tolkien", True),
        ("Daft Punk", "Data Punk", False),
        ("Herbert", "Frank Herberts", False),
    ],
)
def test_author_matches(author, candidate, expected):
    assert author_matches(author, {"author": candidate}) is expected


def test_the_module_reads_no_tags_twice(tags, monkeypatch):
    calls = []
    real = MusicFileOperations.read_metadata
    monkeypatch.setattr(
        MusicFileOperations,
        "read_metadata",
        lambda self, path: calls.append(path) or real(self, path),
    )

    batch.parse_album([Path("/m/a/01.mp3"), Path("/m/a/02.mp3")])

    assert len(calls) == 2
