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
from sok.config.config_manager import ConfigManager, env_keys_win


@pytest.fixture
def make_config(tmp_path, monkeypatch):
    """A config manager of its own, without the .env of the repository."""
    monkeypatch.setenv("SOK_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(config_manager, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("SOK_ENV_KEYS_WIN", raising=False)

    def make(user_key="", env_key=None):
        if env_key is None:
            monkeypatch.delenv("API_KEY_TMDB_V4", raising=False)
        else:
            monkeypatch.setenv("API_KEY_TMDB_V4", env_key)
        config = ConfigManager(tmp_path / "config.json")
        if user_key:
            config.set("api_key_tmdb_v4", user_key)
        return config

    return make


def test_the_key_of_the_settings_wins_by_default(make_config):
    config = make_config(user_key="typed", env_key="from-env")

    assert config.get("api_key_tmdb_v4") == "typed"
    assert not config.env_locked("api_key_tmdb_v4")


def test_the_environment_wins_with_sok_env_keys_win(make_config, monkeypatch):
    config = make_config(user_key="typed", env_key="from-env")
    monkeypatch.setenv("SOK_ENV_KEYS_WIN", "1")

    assert config.get("api_key_tmdb_v4") == "from-env"
    assert config.env_locked("api_key_tmdb_v4")
    # The typed key is kept, for when the variable is removed.
    assert config.get_user_value("api_key_tmdb_v4") == "typed"


def test_without_an_environment_key_the_settings_are_used(make_config, monkeypatch):
    config = make_config(user_key="typed")
    monkeypatch.setenv("SOK_ENV_KEYS_WIN", "true")

    assert config.get("api_key_tmdb_v4") == "typed"
    assert not config.env_locked("api_key_tmdb_v4")


def test_build_constants_never_win_over_the_settings(make_config, monkeypatch):
    config = make_config(user_key="typed")
    config._runtime_values["api_key_tmdb_v4"] = "project key"
    monkeypatch.setenv("SOK_ENV_KEYS_WIN", "1")

    assert config.get("api_key_tmdb_v4") == "typed"


@pytest.mark.parametrize(
    "value, expected",
    [("1", True), ("TRUE", True), (" yes ", True), ("on", True), ("0", False)],
)
def test_the_values_of_the_variable(monkeypatch, value, expected):
    monkeypatch.setenv("SOK_ENV_KEYS_WIN", value)

    assert env_keys_win() is expected


def test_the_variable_unset(monkeypatch):
    monkeypatch.delenv("SOK_ENV_KEYS_WIN", raising=False)

    assert not env_keys_win()
