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

from sok.config.config_manager import xdg_dir


def test_uses_absolute_variable(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert xdg_dir("XDG_DATA_HOME", ".local/share") == tmp_path / "S.O.K"


def test_falls_back_when_unset(monkeypatch):
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    expected = Path.home() / ".local/state" / "S.O.K"
    assert xdg_dir("XDG_STATE_HOME", ".local/state") == expected


def test_ignores_relative_variable(monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", "relative/dir")
    expected = Path.home() / ".local/share" / "S.O.K"
    assert xdg_dir("XDG_DATA_HOME", ".local/share") == expected


def test_the_windows_install_folder_is_the_resolved_one(monkeypatch, tmp_path):
    # Windows may give the executable in its short form (C:\PROGRA~1\...),
    # shown as it was on the history page; resolving gives the real path.
    from sok.config import config_manager

    real = tmp_path / "S.O.K"
    real.mkdir()
    (real / "SOK.exe").touch()
    alias = tmp_path / "SOED4C~1.K"
    alias.symlink_to(real)
    monkeypatch.setattr(config_manager, "IS_COMPILED", True)
    monkeypatch.setattr(config_manager.sys, "platform", "win32")
    monkeypatch.setattr(config_manager.sys, "executable", str(alias / "SOK.exe"))

    assert config_manager.get_base_path() == real.resolve()
