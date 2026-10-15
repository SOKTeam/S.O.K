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
    def __init__(self, root, label="", ready=True):
        self._root, self._label, self._ready = root, label, ready

    def rootPath(self):
        return self._root

    def name(self):
        return self._label

    def isValid(self):
        return True

    def isReady(self):
        return self._ready


def test_keeps_system_home_and_mounted_disks(monkeypatch):
    volumes = [
        FakeVolume("/"),
        FakeVolume("/home", "home-data"),
        FakeVolume("/boot/efi"),
        FakeVolume("/run/user/1000"),
        FakeVolume("/snap/core22/1380"),
        FakeVolume("/tmp/.mount_SOKxyz"),
        FakeVolume("/media/will/Films", "Films"),
        FakeVolume("/run/media/will/Backup"),
        FakeVolume("/mnt/nas"),
        FakeVolume("/media/will/Ejecting", ready=False),
    ]
    monkeypatch.setattr(
        home_page.QStorageInfo, "mountedVolumes", staticmethod(lambda: volumes)
    )
    monkeypatch.setattr(home_page, "tr", lambda key, default: default)

    assert home_page.linux_volumes() == {
        "/": "System",
        "/home": "home-data",
        "/media/will/Films": "Films",
        "/run/media/will/Backup": "Backup",
        "/mnt/nas": "nas",
    }


def test_system_disk_keeps_its_label(monkeypatch):
    volumes = [FakeVolume("/", "Fedora")]
    monkeypatch.setattr(
        home_page.QStorageInfo, "mountedVolumes", staticmethod(lambda: volumes)
    )

    assert home_page.linux_volumes() == {"/": "Fedora"}
