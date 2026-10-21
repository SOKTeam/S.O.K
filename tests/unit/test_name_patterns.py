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

from sok.core import name_patterns
from sok.core.interfaces import ContentType
from sok.core.name_patterns import (
    BOOK,
    BUILTIN,
    EPISODE,
    GAME,
    MOVIE,
    MUSIC,
    check_pattern,
    match_name,
)
from sok.file_operations import (
    BookFileOperations,
    GameFileOperations,
    MusicFileOperations,
    VideoFileOperations,
)
from sok.file_operations.detection import detect_sources


@pytest.fixture
def patterns(monkeypatch):
    """Set the input patterns of the settings: patterns(kind, [...])."""
    saved = {}
    monkeypatch.setattr(name_patterns, "user_patterns", lambda k: saved.get(k, []))

    def set_patterns(kind, values):
        saved[kind] = values

    return set_patterns


def test_a_pattern_reads_text_and_numbers():
    found = match_name(
        MUSIC,
        "Daft Punk - 2001 - Discovery - 01 - One More Time",
        ["{artist} - {year} - {album} - {track} - {title}"],
    )
    assert found.values == {
        "artist": "Daft Punk",
        "year": 2001,
        "album": "Discovery",
        "track": 1,
        "title": "One More Time",
    }


def test_spaces_dots_and_underscores_are_the_same_separator():
    for name in ["Dune 2021 1080p", "Dune.2021.1080p", "Dune_2021_WEB-DL"]:
        found = match_name(MOVIE, name, ["{title} {year} {ignore}"])
        assert found.values == {"title": "Dune", "year": 2021}


def test_dots_of_a_title_become_spaces():
    found = match_name(MOVIE, "The.Dark.Knight.2008.x264", ["{title} {year} {ignore}"])
    assert found.values["title"] == "The Dark Knight"


def test_the_year_is_the_last_one():
    found = match_name(
        MOVIE, "Blade.Runner.2049.2017.1080p", ["{title} {year} {ignore}"]
    )
    assert found.values == {"title": "Blade Runner 2049", "year": 2017}


def test_spaces_around_a_dash_are_optional():
    found = match_name(BOOK, "Dune-Frank Herbert", ["{title} - {author}"])
    assert found.values == {"title": "Dune", "author": "Frank Herbert"}


def test_glued_numbers_take_two_digits_for_the_second():
    for name in ["Lost - 0105", "Lost - 105"]:
        found = match_name(EPISODE, name, ["{title} - {season}{episode}"])
        assert found.values == {"title": "Lost", "season": 1, "episode": 5}


def test_the_first_matching_pattern_wins():
    found = match_name(
        BOOK, "Dune (1965)", ["{author} - {title}", "{title} ({year})", "{title}"]
    )
    assert found.pattern == "{title} ({year})"


def test_no_pattern_matches():
    assert match_name(MOVIE, "Dune", ["{title} ({year})"]) is None


@pytest.mark.parametrize(
    ("kind", "pattern", "code", "name"),
    [
        (MOVIE, "{title", "braces", ""),
        (MOVIE, "{title} {quality}", "unknown", "quality"),
        (MOVIE, "{title} {title}", "twice", "title"),
        (EPISODE, "{title} {season}", "required", "episode"),
        (MUSIC, "{track} {artist}", "required", "title"),
    ],
)
def test_invalid_patterns(kind, pattern, code, name):
    error = check_pattern(kind, pattern)
    assert (error.code, error.name) == (code, name)


def test_the_default_forms_shown_are_valid_patterns():
    for kind, forms in BUILTIN.items():
        for form in forms:
            assert check_pattern(kind, form) is None, form


def test_video_names_follow_the_episode_pattern(patterns):
    patterns(EPISODE, ["{episode} - {episode_title}"])

    info = VideoFileOperations().extract_info_from_filename("05 - The Fly.mkv")

    assert info["type"] == "series"
    assert (info["season"], info["episode"]) == (1, 5)
    assert info["episode_title"] == "The Fly"
    assert info["pattern"] == "{episode} - {episode_title}"


def test_video_names_follow_the_movie_pattern(patterns):
    # "1.05" would be read as season 1, episode 5 without the pattern.
    patterns(MOVIE, ["{title} [{year}] {ignore}"])

    info = VideoFileOperations().extract_info_from_filename("Apollo 1.05 [1995] x.mkv")

    assert (info["type"], info["title"], info["year"]) == ("movie", "Apollo 1.05", 1995)
    assert info["episode"] is None


def test_other_names_follow_their_pattern(patterns):
    patterns(MUSIC, ["{artist} - {year} - {album} - {track} - {title}"])
    patterns(BOOK, ["{title} - {author} - {year}"])
    patterns(GAME, ["{title} [{platform}]"])

    track = MusicFileOperations().extract_info_from_filename(
        "Daft Punk - 2001 - Discovery - 01 - One More Time.mp3"
    )
    book = BookFileOperations().extract_info_from_filename(
        "Dune - Frank Herbert - 1965.epub"
    )
    game = GameFileOperations().extract_info_from_filename("Chrono Trigger [SNES].sfc")

    assert (track["artist"], track["album"], track["track_number"]) == (
        "Daft Punk",
        "Discovery",
        1,
    )
    assert (book["title"], book["author"], book["year"]) == (
        "Dune",
        "Frank Herbert",
        1965,
    )
    assert (game["title"], game["platform"]) == ("Chrono Trigger", "Super Nintendo")


def test_names_without_a_matching_pattern_use_the_default_rules(patterns):
    patterns(BOOK, ["{title} - {author} - {year}"])

    info = BookFileOperations().extract_info_from_filename("Frank Herbert - Dune.epub")

    assert (info["author"], info["title"]) == ("Frank Herbert", "Dune")
    assert "pattern" not in info


def test_detection_takes_a_pattern_episode_as_an_episode(patterns, tmp_path):
    patterns(EPISODE, ["{title} - Episode {episode}"])
    (tmp_path / "Severance - Episode 3.mkv").write_bytes(b"")

    report = detect_sources([tmp_path])

    assert [(g.kind, g.title) for g in report.groups] == [
        (ContentType.EPISODE, "Severance")
    ]
    assert report.to_check == []


def test_detection_keeps_a_pattern_movie_a_movie(patterns, tmp_path):
    patterns(MOVIE, ["{title} [{year}]"])
    path = Path(tmp_path / "Apollo 1.05 [1995].mkv")
    path.write_bytes(b"")

    report = detect_sources([tmp_path])

    assert [g.kind for g in report.groups] == [ContentType.MOVIE]
