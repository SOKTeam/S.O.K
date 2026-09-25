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

from sok.core.media_manager import UniversalMediaManager
from sok.file_operations import organize
from sok.file_operations.book_operations import BookFileOperations
from sok.file_operations.game_operations import GameFileOperations
from sok.file_operations.music_operations import MusicFileOperations
from sok.media.books.book import Book
from sok.media.games.game import Game
from sok.media.music.album import Album


class FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


@pytest.fixture(autouse=True)
def config(monkeypatch):
    cfg = FakeConfig(skip_duplicates=False, backup_before_rename=False)
    monkeypatch.setattr(organize, "get_config_manager", lambda: cfg)
    return cfg


def make_file(tmp_path, name):
    source = tmp_path / "downloads" / name
    source.parent.mkdir(exist_ok=True)
    source.write_text("content")
    dest = tmp_path / "library"
    dest.mkdir(exist_ok=True)
    return source, dest


class TestOrganizeFilesList:
    def test_music_goes_to_artist_album_folder(self, tmp_path):
        source, dest = make_file(tmp_path, "01 - Paranoid Android.mp3")
        album = Album("OK Computer", "Radiohead", 1997)

        report = MusicFileOperations().organize_files_list([source], str(dest), album)

        assert report["errors"] == []
        assert report["total_moved"] == 1
        album_folder = dest.joinpath(*album.get_folder_structure())
        assert [p.name for p in album_folder.iterdir()] == ["01 - Paranoid Android.mp3"]
        assert not source.exists()

    def test_book_goes_to_book_folder(self, tmp_path):
        source, dest = make_file(tmp_path, "Frank Herbert - Dune.epub")
        book = Book("Dune", "en", UniversalMediaManager())
        book.author = "Frank Herbert"

        report = BookFileOperations().organize_files_list([source], str(dest), book)

        assert report["errors"] == []
        assert dest.joinpath(*book.get_folder_structure()).is_dir()
        assert not source.exists()

    def test_game_goes_to_game_folder(self, tmp_path):
        source, dest = make_file(tmp_path, "Super Mario World (USA).sfc")
        game = Game("Super Mario World", "en", UniversalMediaManager())

        report = GameFileOperations().organize_files_list([source], str(dest), game)

        assert report["errors"] == []
        assert dest.joinpath(*game.get_folder_structure()).is_dir()
        assert not source.exists()

    def test_without_media_item_files_go_to_destination(self, tmp_path):
        source, dest = make_file(tmp_path, "01 - Airbag.mp3")

        report = MusicFileOperations().organize_files_list([source], str(dest), None)

        assert report["errors"] == []
        assert (dest / "01 - Airbag.mp3").exists()

    def test_skip_duplicates(self, tmp_path, config):
        config._values["skip_duplicates"] = True
        source, dest = make_file(tmp_path, "01 - Airbag.mp3")
        (dest / "01 - Airbag.mp3").write_text("existing")

        report = MusicFileOperations().organize_files_list([source], str(dest), None)

        assert report["total_moved"] == 0
        assert len(report["skipped"]) == 1
        assert source.exists()
