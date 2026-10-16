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
import os
import platform
import sys

import pytest
import requests

from sok.core import updater
from sok.core.updater import UpdateManager

RELEASE = {
    "html_url": "https://example.com/release",
    "assets": [
        {"name": "SOK_macOS_v1.2.0.dmg", "browser_download_url": "dmg-url"},
        {"name": "SOK_Setup_v1.2.0.exe", "browser_download_url": "exe-url"},
        {"name": "SOK_Linux_v1.2.0_aarch64.AppImage", "browser_download_url": "arm"},
        {"name": "SOK_Linux_v1.2.0_x86_64.AppImage", "browser_download_url": "x64"},
    ],
}


@pytest.fixture
def manager():
    m = UpdateManager()
    m.latest_release = RELEASE
    return m


def test_windows_downloads_the_setup(manager, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")

    assert manager.get_download_url() == "exe-url"


def test_macos_downloads_the_disk_image(manager, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")

    assert manager.get_download_url() == "dmg-url"


def test_macos_falls_back_to_the_release_page(manager, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    manager.latest_release = {**RELEASE, "assets": RELEASE["assets"][1:]}

    assert manager.get_download_url() == "https://example.com/release"


@pytest.fixture
def appimage(monkeypatch, tmp_path):
    """Pretend to run on Linux from tmp_path/SOK.AppImage."""
    path = tmp_path / "SOK.AppImage"
    path.write_bytes(b"old")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("APPIMAGE", str(path))
    return path


def test_linux_downloads_the_appimage_of_this_machine(manager, appimage, monkeypatch):
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")

    assert manager.get_download_url() == "x64"


def test_linux_outside_an_appimage_opens_the_release_page(manager, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("APPIMAGE", raising=False)

    assert manager.get_download_url() == "https://example.com/release"


def test_replace_appimage_swaps_the_file_in_place(manager, appimage, monkeypatch):
    def download(url, target, progress_callback=None):
        target.write_bytes(b"new")

    monkeypatch.setattr(UpdateManager, "_download", staticmethod(download))

    manager.replace_appimage("x64")

    assert appimage.read_bytes() == b"new"
    assert os.access(appimage, os.X_OK)
    assert list(appimage.parent.iterdir()) == [appimage]


def test_failed_download_keeps_the_old_appimage(manager, appimage, monkeypatch):
    def download(url, target, progress_callback=None):
        target.write_bytes(b"partial")
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(UpdateManager, "_download", staticmethod(download))

    with pytest.raises(OSError, match="network down"):
        manager.replace_appimage("x64")

    assert appimage.read_bytes() == b"old"
    assert list(appimage.parent.iterdir()) == [appimage]


def test_not_an_appimage_on_other_platforms(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPIMAGE", "/tmp/SOK.AppImage")

    assert updater.running_appimage() is None
