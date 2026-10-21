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


from sok.core.batch import (
    STATUS_AMBIGUOUS,
    STATUS_READY,
    evaluate,
    parse_track,
    same_track,
)
from sok.file_operations import MusicFileOperations
from sok.media.music.track import Track
from sok.ui.factories.media_factory import create_media_item
from sok.ui.pages.tracks_page import describe_track


def track(title, album, album_type="album", date="2017-06-23", number=None):
    return {
        "title": title,
        "artist": "Crumb",
        "album": album,
        "album_type": album_type,
        "release_date": date,
        "track_number": number,
    }


@pytest.fixture(autouse=True)
def default_music_format(monkeypatch):
    """Name tracks with the default format, whatever the local settings say."""
    from sok.file_operations import music_operations

    class Config:
        def get(self, key, default=None):
            return default

    monkeypatch.setattr(music_operations, "get_config_manager", lambda: Config())


LOCKET = [
    track("Locket", "Locket", "ep", "2017-06-23", 4),
    track("Locket", "warm songs for cold weather", "album", "2017-11-08", 10),
    track("Locket", "SXSW 2018", "compilation", "2018"),
]


def test_the_album_of_the_tags_makes_the_track_ready():
    assert evaluate(
        "Locket", None, LOCKET, "Crumb", same_track, "warm songs for cold weather"
    ) == (
        1,
        STATUS_READY,
    )


def test_a_track_on_two_albums_without_album_tag_is_to_pick():
    assert evaluate("Locket", None, LOCKET, "Crumb", same_track) == (
        0,
        STATUS_AMBIGUOUS,
    )


def test_compilations_do_not_count_as_another_album():
    results = [LOCKET[0], LOCKET[2]]
    assert evaluate("Locket", None, results, "Crumb", same_track) == (0, STATUS_READY)


def test_another_artist_is_not_the_track():
    results = [{**LOCKET[0], "artist": "Someone"}]
    assert evaluate("Locket", None, results, "Crumb", same_track)[1] == STATUS_AMBIGUOUS


def test_track_is_read_from_its_tags_first(monkeypatch):
    monkeypatch.setattr(
        MusicFileOperations,
        "read_metadata",
        lambda self, path: {"title": "Locket", "artist": "Crumb", "album": "Locket"},
    )

    parsed = parse_track([Path("01 - track.flac")])

    assert (parsed.query, parsed.title, parsed.author, parsed.album) == (
        "Locket Crumb",
        "Locket",
        "Crumb",
        "Locket",
    )
    assert parsed.search_kwargs == {"title": "Locket", "artist": "Crumb"}


def make_track(**data):
    return create_media_item(
        {"id": 1, "title": "Locket", "artist": "Crumb", **data}, "track", None
    )


def test_track_is_named_with_the_music_format():
    item = make_track(album="Locket", track_number=4, release_date="2017-06-23")
    assert MusicFileOperations().format_track(item, ".flac") == [
        "Crumb - Locket",
        "04 - Locket.flac",
    ]


def test_missing_values_leave_no_separator():
    assert MusicFileOperations().format_track(make_track(), ".mp3") == [
        "Crumb",
        "Locket.mp3",
    ]


def test_music_format_of_the_settings_is_used(monkeypatch):
    from sok.file_operations import music_operations

    class Config:
        def get(self, key, default=None):
            return (
                "{artist}/{year} - {album}/{track}. {title}"
                if key == "music_format"
                else default
            )

    monkeypatch.setattr(music_operations, "get_config_manager", lambda: Config())
    item = make_track(album="Locket", track_number=4, release_date="2017-06-23")

    assert MusicFileOperations().format_track(item, ".flac") == [
        "Crumb",
        "2017 - Locket",
        "04. Locket.flac",
    ]


def test_track_number_of_the_tags_is_used_on_the_same_album(monkeypatch):
    monkeypatch.setattr(
        MusicFileOperations,
        "read_metadata",
        lambda self, path: {"album": "Locket", "track_number": 4},
    )
    ops = MusicFileOperations()

    same = ops.batch_target(make_track(album="Locket"), Path("/x/a.flac"), True)
    other = ops.batch_target(make_track(album="Other"), Path("/x/a.flac"), True)

    assert same == (["Crumb - Locket"], "04 - Locket.flac")
    assert other == (["Crumb - Other"], "Locket.flac")


def test_track_in_the_menu_shows_its_album_and_year():
    assert describe_track(LOCKET[0]) == "Locket — Crumb (Locket, 2017)"


def test_track_model_can_be_created():
    assert Track(
        "Locket", "en", None, artist="Crumb", album="Locket"
    ).get_folder_structure() == [
        "Crumb",
        "Locket",
    ]


def test_artist_and_title_come_from_a_single_file_name(monkeypatch):
    monkeypatch.setattr(MusicFileOperations, "read_metadata", lambda self, path: {})

    parsed = parse_track([Path("Daft Punk - Get Lucky.mp3")])

    assert (parsed.title, parsed.author) == ("Get Lucky", "Daft Punk")
