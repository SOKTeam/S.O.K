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
from sok.ui.components.integrations.oauth import OAuthManager
from sok.ui.components.settings import api_section
from sok.ui.components.settings.api_section import ApiSection
from sok.ui.i18n import tr


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("SOK_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(config_manager, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("API_KEY_RAWG", raising=False)
    return ConfigManager(tmp_path / "config.json")


@pytest.fixture
def section(qtbot, config, monkeypatch):
    resets = []
    monkeypatch.setattr(api_section, "reset_media_manager", lambda: resets.append(1))
    widget = ApiSection(config, OAuthManager())
    widget.resets = resets
    qtbot.addWidget(widget)
    widget.load()
    return widget


def type_key(field, text):
    field.setText(text)
    field.editingFinished.emit()


def test_a_typed_key_is_saved(section, config, tmp_path):
    type_key(section._rawg_input, "  my-rawg-key  ")

    assert config.get_user_value("api_key_rawg") == "my-rawg-key"
    assert section._rawg_input.text() == "my-rawg-key"
    assert "my-rawg-key" in ConfigManager(tmp_path / "config.json").get("api_key_rawg")
    assert section.resets == [1]


def test_an_emptied_field_removes_the_key(section, config):
    type_key(section._rawg_input, "my-rawg-key")

    type_key(section._rawg_input, "")

    assert config.get_user_value("api_key_rawg") == ""


def test_leaving_a_field_unchanged_saves_nothing(section):
    type_key(section._rawg_input, "")

    assert section.resets == []


def test_lastfm_takes_a_key_without_a_secret(section, config):
    assert not hasattr(section, "_lastfm_connect_btn")

    type_key(section._lastfm_input, "my-lastfm-key")

    assert config.get_user_value("api_key_lastfm") == "my-lastfm-key"


def test_each_service_line_tells_its_state(section, config):
    assert section._rows["deezer"].value.text().startswith(tr("settings_src_free"))
    assert section._rows["rawg"].value.text() == tr("settings_src_to_set_up")

    type_key(section._rawg_input, "my-rawg-key")

    assert section._rows["rawg"].value.text() == tr("settings_src_your_key")


def preferred():
    return "· " + tr("settings_src_preferred", "preferred")


def test_the_preferred_service_is_marked_and_can_change(section, config):
    config.set("preferred_api_music", "deezer")
    section.load()
    assert section._rows["deezer"].value.text().endswith(preferred())
    assert section._prefer_keys["deezer"].isHidden()

    section._prefer_keys["musicbrainz"].click()

    assert config.get("preferred_api_music") == "musicbrainz"
    assert section._rows["musicbrainz"].value.text().endswith(preferred())
    assert not section._rows["deezer"].value.text().endswith(preferred())


def test_a_preferred_service_without_its_key_is_a_warning(section, config):
    config.set("preferred_api_games", "rawg")
    section.load()

    assert section._rows["rawg"].value.property("tone") == "warn"


def test_a_click_opens_one_line_at_a_time(section):
    section._toggle("rawg")
    section._toggle("tmdb")

    assert section._rows["tmdb"].is_open()
    assert not section._rows["rawg"].is_open()
