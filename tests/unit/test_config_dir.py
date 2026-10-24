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
from sok.config import config_manager
from sok.config.config_manager import ConfigManager, data_dir, log_dir


def test_without_the_variable_the_paths_stay_those_of_today(monkeypatch):
    monkeypatch.delenv("SOK_CONFIG_DIR", raising=False)

    assert data_dir() == config_manager.BASE_PATH / "data"
    assert log_dir() == config_manager.BASE_PATH / "logs"


def test_sok_config_dir_holds_the_settings_the_key_and_the_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("SOK_CONFIG_DIR", str(tmp_path / "config"))

    assert data_dir() == tmp_path / "config"
    assert log_dir() == tmp_path / "config" / "logs"

    config = ConfigManager()
    config.set("language", "fr")

    assert config.config_path == tmp_path / "config" / "config.json"
    assert (tmp_path / "config" / "config.json").exists()
    assert (tmp_path / "config" / ".local.key").exists()


def test_an_empty_variable_is_ignored(monkeypatch):
    monkeypatch.setenv("SOK_CONFIG_DIR", "  ")

    assert data_dir() == config_manager.BASE_PATH / "data"


def test_a_relative_folder_is_made_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SOK_CONFIG_DIR", "config")

    assert data_dir() == tmp_path / "config"
