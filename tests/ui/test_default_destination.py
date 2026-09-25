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

from sok.ui.components.organize.options_panel import OptionsPanel
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
    def test_panel_uses_default_folder_of_its_media_type(self, qtbot, tmp_path, config):
        config._values["default_music_path"] = str(tmp_path)

        panel = OptionsPanel("music")
        qtbot.addWidget(panel)

        assert panel.get_destination_path() == tmp_path

    def test_missing_folder_is_ignored(self, qtbot, tmp_path, config):
        config._values["default_books_path"] = str(tmp_path / "missing")

        panel = OptionsPanel("book")
        qtbot.addWidget(panel)

        assert panel.get_destination_path() is None

    def test_default_set_after_startup_is_applied_on_show(
        self, qtbot, tmp_path, config
    ):
        panel = OptionsPanel("game")
        qtbot.addWidget(panel)
        assert panel.get_destination_path() is None

        config._values["default_games_path"] = str(tmp_path)
        panel.show()

        assert panel.get_destination_path() == tmp_path

    def test_user_choice_is_kept_on_show(self, qtbot, tmp_path, config):
        chosen = tmp_path / "chosen"
        chosen.mkdir()
        config._values["default_video_path"] = str(tmp_path)
        panel = OptionsPanel("video")
        qtbot.addWidget(panel)

        panel._dest_drop.set_path(chosen)
        panel.show()

        assert panel.get_destination_path() == chosen
