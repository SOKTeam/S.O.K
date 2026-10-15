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
