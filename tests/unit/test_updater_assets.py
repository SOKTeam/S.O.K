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

import pytest

from sok.core.updater import UpdateManager

RELEASE = {
    "html_url": "https://example.com/release",
    "assets": [
        {"name": "SOK_macOS_v1.2.0.dmg", "browser_download_url": "dmg-url"},
        {"name": "SOK_Setup_v1.2.0.exe", "browser_download_url": "exe-url"},
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
