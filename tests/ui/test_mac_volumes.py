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
from sok.ui.pages import home_page


class FakeVolume:
    def __init__(self, root, name="", ready=True):
        self._root, self._name, self._ready = root, name, ready

    def rootPath(self):
        return self._root

    def displayName(self):
        return self._name

    def isValid(self):
        return True

    def isReady(self):
        return self._ready


def test_keeps_the_startup_disk_and_mounted_volumes(monkeypatch):
    volumes = [
        FakeVolume("/", "Macintosh HD"),
        FakeVolume("/System/Volumes/Data", "Data"),
        FakeVolume("/Volumes/Media", "Media"),
        FakeVolume("/Volumes/Backup", ""),
        FakeVolume("/Volumes/Ejecting", "Ejecting", ready=False),
    ]
    monkeypatch.setattr(
        home_page.QStorageInfo, "mountedVolumes", staticmethod(lambda: volumes)
    )

    assert home_page.mac_volumes() == {
        "/": "Macintosh HD",
        "/Volumes/Media": "Media",
        "/Volumes/Backup": "Backup",
    }
