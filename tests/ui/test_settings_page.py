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

from sok.config import config_manager
from sok.config.config_manager import ConfigManager
from sok.ui.components.settings.formats_section import (
    MODELS,
    FormatsSection,
    allowed_variables,
    model_error,
)
from sok.ui.components.settings.layout import Choice, Switch
from sok.ui.components.settings.paths_section import PathsSection
from sok.ui.components.settings.preview import _CLOSE, _OPEN, preview_parts


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("SOK_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(config_manager, "load_dotenv", lambda *a, **k: None)
    return ConfigManager(tmp_path / "config.json")


def plain(parts):
    return [p.replace(_OPEN, "").replace(_CLOSE, "") for p in parts]


class TestModelError:
    def test_known_variables_are_accepted(self):
        movie = MODELS[0]
        assert model_error("{title} ({year}) {quality}", allowed_variables(movie)) == ""

    def test_series_numbers_without_a_key_are_accepted(self):
        series = next(m for m in MODELS if m.config_key == "video_format")
        assert (
            model_error("{title} {season_num}x{episode_num}", allowed_variables(series))
            == ""
        )

    def test_an_unknown_variable_is_refused(self):
        assert "{director}" in model_error("{title} {director}", ["title"])

    def test_an_open_brace_is_refused(self):
        assert model_error("{title", ["title"])

    def test_a_number_is_refused(self):
        assert model_error("{0}", ["title"])

    def test_an_empty_model_is_refused(self):
        assert model_error("  ", ["title"])


class TestPreviewParts:
    def test_movie_name_like_the_renaming(self):
        assert plain(preview_parts("movie_format", "{title} ({year})")) == [
            "Oppenheimer (2023).mkv"
        ]

    def test_filled_values_are_marked(self):
        assert preview_parts("movie_format", "{title}") == [
            f"{_OPEN}Oppenheimer{_CLOSE}.mkv"
        ]

    def test_music_slashes_make_folders(self):
        parts = plain(
            preview_parts("music_format", "{artist} - {album}/{track} - {title}")
        )
        assert parts == ["Daft Punk - Discovery", "01 - One More Time.flac"]

    def test_a_slash_in_a_movie_model_is_removed(self):
        assert plain(preview_parts("movie_format", "{title}/{year}")) == [
            "Oppenheimer2023.mkv"
        ]

    def test_a_model_without_values_gives_no_name(self):
        assert preview_parts("book_format", "{series}") == []


@pytest.fixture
def formats(qtbot, config):
    section = FormatsSection(config)
    qtbot.addWidget(section)
    section.retranslate()
    return section


class TestFormatsSection:
    def test_every_model_is_a_line_with_its_value(self, formats, config):
        for model in MODELS:
            assert formats._rows[model.config_key].value.text() == config.get(
                model.config_key
            )

    def test_a_click_opens_the_line_and_its_field(self, formats, config):
        formats._toggle("book_format")

        assert formats._rows["book_format"].is_open()
        assert formats._input.text() == config.get("book_format")
        assert formats.current().config_key == "book_format"

    def test_opening_a_line_closes_the_other(self, formats):
        formats._toggle("book_format")
        formats._toggle("game_format")

        assert not formats._rows["book_format"].is_open()
        assert formats._rows["game_format"].is_open()

    def test_a_valid_model_is_saved_and_shown_on_its_line(self, formats, config):
        formats._toggle("movie_format")
        formats._input.setText("{title} [{year}]")
        formats._toggle("movie_format")  # closing saves

        assert config.get("movie_format") == "{title} [{year}]"
        assert formats._rows["movie_format"].value.text() == "{title} [{year}]"

    def test_an_invalid_model_is_not_saved(self, formats, config):
        before = config.get("movie_format")
        formats._toggle("movie_format")

        formats._input.setText("{title} {director}")
        formats._save()

        assert config.get("movie_format") == before
        assert not formats._error.isHidden()

    def test_a_variable_is_inserted_at_the_cursor(self, formats, config):
        formats._toggle("movie_format")
        formats._input.setText("{title} ")

        formats._insert("{quality}")

        assert config.get("movie_format") == "{title} {quality}"


class TestPathsSection:
    def test_series_show_they_follow_the_movies(self, qtbot, config, tmp_path):
        config.set("default_video_path", str(tmp_path))
        section = PathsSection(config)
        qtbot.addWidget(section)

        section.load()

        label = section._paths["default_series_path"]
        assert label.property("empty") == "true"
        assert section._paths["default_video_path"].toolTip() == str(tmp_path)


class TestWidgets:
    def test_switch_toggles_and_emits(self, qtbot):
        box = Switch()
        qtbot.addWidget(box)
        seen = []
        box.toggled.connect(seen.append)

        box.toggle()
        box.setChecked(True)

        assert box.isChecked()
        assert seen == [True]

    def test_choice_marks_one_key(self, qtbot):
        choice = Choice(["a", "b"])
        qtbot.addWidget(choice)
        seen = []
        choice.chosen.connect(seen.append)

        choice._click("b")
        choice._click("b")

        assert choice.value() == "b"
        assert seen == ["b"]
