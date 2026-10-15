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
import sys
from pathlib import Path

import pytest

from sok.core.desktop_entry import desktop_entry, exec_argument, install_desktop_entry

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = (ROOT / "packaging" / "linux" / "com.sokteam.sok.desktop").read_text(
    encoding="utf-8"
)


def test_quotes_a_plain_path():
    assert exec_argument(Path("/home/me/Apps/SOK.AppImage")) == (
        '"/home/me/Apps/SOK.AppImage"'
    )


def test_escapes_reserved_characters():
    path = Path('/home/me/My $Apps/50% "off"/SOK.AppImage')

    assert exec_argument(path) == r'"/home/me/My \\$Apps/50%% \\"off\\"/SOK.AppImage"'


def test_entry_runs_the_appimage():
    entry = desktop_entry(TEMPLATE, Path("/home/me/Apps/SOK.AppImage"))

    assert 'Exec="/home/me/Apps/SOK.AppImage"' in entry.splitlines()
    assert "TryExec=/home/me/Apps/SOK.AppImage" in entry.splitlines()
    assert "Icon=com.sokteam.sok" in entry.splitlines()
    assert "Exec=SOK" not in entry


@pytest.fixture
def appimage(monkeypatch, tmp_path):
    """Pretend to run on Linux from an AppImage mounted at tmp_path/mount."""
    appdir = tmp_path / "mount"
    appdir.mkdir()
    (appdir / "com.sokteam.sok.desktop").write_text(TEMPLATE, encoding="utf-8")
    (appdir / "com.sokteam.sok.png").write_bytes(b"png")
    path = tmp_path / "SOK.AppImage"
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("APPIMAGE", str(path))
    monkeypatch.setenv("APPDIR", str(appdir))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return tmp_path


def test_installs_entry_and_icon(appimage):
    install_desktop_entry()

    data = appimage / "data"
    entry = data / "applications" / "com.sokteam.sok.desktop"
    icon = data / "icons" / "hicolor" / "512x512" / "apps" / "com.sokteam.sok.png"
    assert f'Exec="{appimage / "SOK.AppImage"}"' in entry.read_text(encoding="utf-8")
    assert icon.read_bytes() == b"png"


def test_leaves_unchanged_files_alone(appimage):
    install_desktop_entry()
    entry = appimage / "data" / "applications" / "com.sokteam.sok.desktop"
    entry.touch()
    mtime = entry.stat().st_mtime_ns
    entry.chmod(0o444)

    install_desktop_entry()

    assert entry.stat().st_mtime_ns == mtime


def test_does_nothing_outside_an_appimage(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("APPIMAGE", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    install_desktop_entry()

    assert list(tmp_path.iterdir()) == []


def test_failure_does_not_stop_the_app(appimage, caplog):
    (appimage / "mount" / "com.sokteam.sok.desktop").unlink()

    install_desktop_entry()

    assert "applications menu" in caplog.text
