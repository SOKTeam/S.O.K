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
from sok.ui.pages.music_page import ALBUM, TRACK, MusicPage, length_text


def touch(folder: Path, *names: str) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for name in names:
        path = folder / name
        path.write_bytes(b"")
        files.append(path)
    return files


def test_an_album_folder_is_one_item_searched_as_an_album(qtbot, tmp_path):
    album = touch(
        tmp_path / "Daft Punk - Discovery (2001)",
        "01 - One More Time.flac",
        "02 - Aerodynamic.flac",
        "03 - Digital Love.flac",
    )
    loose = touch(tmp_path / "Loose", "Radiohead - Paranoid Android.mp3")
    page = MusicPage()
    qtbot.addWidget(page)

    items = page.group_files(album + loose)

    assert sorted(len(item) for item in items) == [1, 3]
    album_item = next(item for item in items if len(item) == 3)
    assert page.search_spec(album_item) is ALBUM
    assert page.search_spec(loose) is TRACK
    assert ALBUM.content_type is ContentType.ALBUM


def test_length_of_a_track():
    assert length_text(320.4) == "5:20"
    assert length_text(None) == ""
