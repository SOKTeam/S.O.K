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

from sok.ui.pages.books_page import BooksPage
from sok.ui.pages.games_page import GamesPage
from sok.ui.pages.movies_page import MoviesPage
from sok.ui.pages.music_page import MusicPage
from sok.ui.controllers import default_paths


class FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


@pytest.fixture
def config(monkeypatch):
    cfg = FakeConfig()
    monkeypatch.setattr(default_paths, "get_config_manager", lambda: cfg)
    return cfg


class TestDefaultDestination:
    def test_page_uses_default_folder_of_its_media_type(self, qtbot, tmp_path, config):
        config._values["default_music_path"] = str(tmp_path)

        page = MusicPage()
        qtbot.addWidget(page)

        assert page._dest_drop.get_path() == tmp_path

    def test_missing_folder_is_ignored(self, qtbot, tmp_path, config):
        config._values["default_books_path"] = str(tmp_path / "missing")

        page = BooksPage()
        qtbot.addWidget(page)

        assert page._dest_drop.get_path() is None

    def test_default_set_after_startup_is_applied_on_show(
        self, qtbot, tmp_path, config
    ):
        page = GamesPage()
        qtbot.addWidget(page)
        assert page._dest_drop.get_path() is None

        config._values["default_games_path"] = str(tmp_path)
        page.show()

        assert page._dest_drop.get_path() == tmp_path

    def test_user_choice_is_kept_on_show(self, qtbot, tmp_path, config):
        chosen = tmp_path / "chosen"
        chosen.mkdir()
        config._values["default_video_path"] = str(tmp_path)
        page = MoviesPage()
        qtbot.addWidget(page)

        page._dest_drop.set_path(chosen)
        page.show()

        assert page._dest_drop.get_path() == chosen
