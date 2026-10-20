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

from sok.core.interfaces import ContentType
from sok.file_operations.detection import MediaTypeDetector, detect_sources


def make(root: Path, *names: str) -> None:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")


def summary(report):
    return [(g.kind, g.title, [f.name for f in g.files]) for g in report.groups]


def test_movies_are_one_group_sorted_naturally(tmp_path):
    make(tmp_path, "Movie 10 (2010).mkv", "Movie 2 (2002).mp4", "Dune (2021).mkv")

    report = detect_sources([tmp_path])

    assert summary(report) == [
        (
            ContentType.MOVIE,
            None,
            ["Dune (2021).mkv", "Movie 2 (2002).mp4", "Movie 10 (2010).mkv"],
        )
    ]
    assert report.to_check == []


def test_episodes_are_grouped_by_series_across_seasons(tmp_path):
    make(
        tmp_path,
        "Severance.S01E02.1080p.mkv",
        "Severance.S01E10.1080p.mkv",
        "severance.s02e01.mkv",
        "Andor 1x03.mkv",
    )

    report = detect_sources([tmp_path])

    assert summary(report) == [
        (ContentType.EPISODE, "Andor", ["Andor 1x03.mkv"]),
        (
            ContentType.EPISODE,
            "Severance",
            [
                "Severance.S01E02.1080p.mkv",
                "Severance.S01E10.1080p.mkv",
                "severance.s02e01.mkv",
            ],
        ),
    ]


def test_episode_without_series_name_takes_it_from_the_folders(tmp_path):
    make(tmp_path, "Severance/Season 1/S01E01.mkv", "Andor S01/S01E02.mkv")

    report = detect_sources([tmp_path])

    assert [(g.kind, g.title) for g in report.groups] == [
        (ContentType.EPISODE, "Andor"),
        (ContentType.EPISODE, "Severance"),
    ]


def test_a_weak_episode_number_is_to_check(tmp_path):
    make(tmp_path, "Star Wars Episode 4 (1977).mkv")

    report = detect_sources([tmp_path])

    assert report.groups == []
    [item] = report.to_check
    assert item.kind == ContentType.EPISODE
    assert not item.certain


def test_a_video_among_episodes_is_to_check(tmp_path):
    make(
        tmp_path,
        "Severance/Season 1/Severance S01E01.mkv",
        "Severance/Season 1/Severance S01E02.mkv",
        "Severance/Season 1/Making of.mkv",
        "Severance/Season 2/Pilot.mkv",
    )

    report = detect_sources([tmp_path])

    assert summary(report) == [
        (
            ContentType.EPISODE,
            "Severance",
            ["Severance S01E01.mkv", "Severance S01E02.mkv"],
        )
    ]
    assert [(d.path.name, d.kind, d.title) for d in report.to_check] == [
        ("Making of.mkv", ContentType.EPISODE, "Severance"),
        ("Pilot.mkv", ContentType.EPISODE, "Severance"),
    ]


def test_one_episode_among_movies_leaves_the_movies_sure(tmp_path):
    make(tmp_path, "Dune (2021).mkv", "Heat (1995).mkv", "Andor S01E01.mkv")

    report = detect_sources([tmp_path])

    assert [(g.kind, len(g.files)) for g in report.groups] == [
        (ContentType.MOVIE, 2),
        (ContentType.EPISODE, 1),
    ]
    assert report.to_check == []


def test_music_is_grouped_by_album_folder_across_discs(tmp_path):
    make(
        tmp_path,
        "Crumb - Locket/01 - Locket.flac",
        "Crumb - Locket/02 - Plants.flac",
        "Crumb - Locket/03 - Bones.flac",
        "The Wall/CD1/01 - In the Flesh.mp3",
        "The Wall/CD1/02 - The Thin Ice.mp3",
        "The Wall/CD2/01 - Hey You.mp3",
    )

    report = detect_sources([tmp_path])

    assert [(g.kind, g.title, len(g.files)) for g in report.groups] == [
        (ContentType.ALBUM, "Crumb - Locket", 3),
        (ContentType.ALBUM, "The Wall", 3),
    ]


def test_audio_files_of_small_folders_are_tracks(tmp_path):
    make(
        tmp_path,
        "Daft Punk - Get Lucky.mp3",
        "Stromae - Alors on danse.mp3",
        "Singles/Crumb - Locket.flac",
    )

    report = detect_sources([tmp_path])

    assert [(g.kind, g.title, len(g.files)) for g in report.groups] == [
        (ContentType.TRACK, None, 3)
    ]


def test_books_and_games_are_one_group_each(tmp_path):
    make(
        tmp_path,
        "Frank Herbert - Dune.epub",
        "Isaac Asimov - Foundation.pdf",
        "Crash Bandicoot (USA).cue",
        "Crash Bandicoot (USA).bin",
        "Super Mario World (USA).sfc",
    )

    report = detect_sources([tmp_path])

    assert [(g.kind, g.title, len(g.files)) for g in report.groups] == [
        (ContentType.BOOK, None, 2),
        (ContentType.GAME, None, 3),
    ]


def test_disc_images_are_to_check_as_games(tmp_path):
    make(tmp_path, "Halo (USA).iso", "Backup.img")

    report = detect_sources([tmp_path])

    assert report.groups == []
    assert [(d.path.name, d.kind) for d in report.to_check] == [
        ("Backup.img", ContentType.GAME),
        ("Halo (USA).iso", ContentType.GAME),
    ]


def test_non_media_hidden_files_and_samples_are_ignored(tmp_path):
    make(
        tmp_path,
        "Dune (2021)/Dune (2021).mkv",
        "Dune (2021)/Sample/Dune-sample.mkv",
        "Dune (2021)/Dune.nfo",
        "Dune (2021)/._Dune (2021).mkv",
        ".hidden/Heat (1995).mkv",
        ".DS_Store",
    )

    report = detect_sources([tmp_path])

    assert summary(report) == [(ContentType.MOVIE, None, ["Dune (2021).mkv"])]
    assert sorted(p.name for p in report.ignored) == [
        ".DS_Store",
        "._Dune (2021).mkv",
        "Dune-sample.mkv",
        "Dune.nfo",
    ]
    assert report.total_files == 1


def test_a_file_dropped_with_its_folder_is_counted_once(tmp_path):
    make(tmp_path, "Dune (2021).mkv")

    report = detect_sources([tmp_path, tmp_path / "Dune (2021).mkv"])

    assert report.total_files == 1


def test_groups_follow_the_page_order(tmp_path):
    make(
        tmp_path,
        "Halo (USA).bin",
        "Frank Herbert - Dune.epub",
        "Album/01 - Track.mp3",
        "Album/02 - Track.mp3",
        "Album/03 - Track.mp3",
        "Single.mp3",
        "Andor S01E01.mkv",
        "Dune (2021).mkv",
    )

    report = detect_sources([tmp_path])

    assert [g.kind for g in report.groups] == [
        ContentType.MOVIE,
        ContentType.EPISODE,
        ContentType.ALBUM,
        ContentType.TRACK,
        ContentType.BOOK,
        ContentType.GAME,
    ]


def test_a_confirmed_file_joins_the_group_of_its_series(tmp_path):
    make(
        tmp_path,
        "Severance/Season 1/Severance S01E01.mkv",
        "Severance/Season 1/Severance S01E02.mkv",
        "Severance/Season 1/Making of.mkv",
    )
    detector = MediaTypeDetector()
    report = detector.detect_sources([tmp_path])

    group = detector.confirm(report, report.to_check[0], ContentType.EPISODE)

    assert report.to_check == []
    assert group.title == "Severance"
    assert [f.name for f in group.files] == [
        "Making of.mkv",
        "Severance S01E01.mkv",
        "Severance S01E02.mkv",
    ]
    assert len(report.groups) == 1


def test_a_confirmed_file_can_change_type(tmp_path):
    make(tmp_path, "Star Wars Episode 4 (1977).mkv", "Halo (USA).iso")
    detector = MediaTypeDetector()
    report = detector.detect_sources([tmp_path])
    halo, star_wars = report.to_check

    detector.confirm(report, star_wars, ContentType.MOVIE)
    detector.confirm(report, halo, ContentType.GAME)

    assert [(g.kind, g.title) for g in report.groups] == [
        (ContentType.MOVIE, None),
        (ContentType.GAME, None),
    ]


def test_generic_files_are_ignored(tmp_path):
    make(tmp_path, "Readme.txt", "Setup.exe", "Movie.part1.rar", "Report.docx")

    report = detect_sources([tmp_path])

    assert report.total_files == 0
    assert len(report.ignored) == 4


def test_a_folder_of_singles_by_several_artists_is_tracks(tmp_path):
    make(
        tmp_path,
        "Singles/Daft Punk - Get Lucky.mp3",
        "Singles/Stromae - Alors on danse.mp3",
        "Singles/Crumb - Locket.mp3",
        "Album/01 - One.mp3",
        "Album/02 - Two.mp3",
        "Album/03 - Three.mp3",
    )

    report = detect_sources([tmp_path])

    assert [(g.kind, g.title, len(g.files)) for g in report.groups] == [
        (ContentType.ALBUM, "Album", 3),
        (ContentType.TRACK, None, 3),
    ]
