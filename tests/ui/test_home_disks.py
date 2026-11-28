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
from collections import namedtuple
from pathlib import Path

from sok.ui.pages import home_page
from sok.ui.pages.home_page import Disk, DiskWorker, HomeScene

Usage = namedtuple("Usage", "total used free")
GB = 1024**3


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


def test_windows_drives_are_named_by_label_and_letter(monkeypatch):
    volumes = [
        FakeVolume("C:/", "Windows"),
        FakeVolume("D:/"),
        FakeVolume("E:/", "Clé", ready=False),
        FakeVolume("C:/Mount/Backup", "Backup"),
    ]
    monkeypatch.setattr(
        home_page.QStorageInfo, "mountedVolumes", staticmethod(lambda: volumes)
    )

    assert home_page.windows_volumes() == {"C:\\": "Windows (C:)", "D:\\": "D:"}


def run_worker(monkeypatch, folders, volumes, sizes):
    monkeypatch.setattr(
        home_page, "_volume_of", lambda path: {"/films": ("/data", "Data")}[str(path)]
    )
    monkeypatch.setattr(home_page, "system_volumes", lambda: volumes)
    monkeypatch.setattr(
        home_page.shutil,
        "disk_usage",
        lambda root: Usage(sizes[root], sizes[root] // 2, sizes[root] // 2),
    )
    worker = DiskWorker([Path(f) for f in folders])
    found = []
    worker.finished.connect(found.extend)
    worker.run()
    return [disk.label for disk in found]


def test_every_disk_is_listed_the_destinations_first(monkeypatch):
    labels = run_worker(
        monkeypatch,
        ["/films"],
        {"/": "System", "/data": "Data again", "/media/usb": "USB"},
        {"/": 500 * GB, "/data": 2000 * GB, "/media/usb": 64 * GB},
    )

    assert labels == ["Data", "System", "USB"]


def test_small_volumes_are_left_out_unless_files_go_there(monkeypatch):
    labels = run_worker(
        monkeypatch,
        ["/films"],
        {"/": "System", "/boot": "Recovery"},
        {"/": 500 * GB, "/data": GB // 2, "/boot": GB // 2},
    )

    assert labels == ["Data", "System"]


def test_the_scene_grows_with_the_disks(qtbot):
    scene = HomeScene()
    qtbot.addWidget(scene)
    scene.set_disks([Disk("A", 10, 5)])
    one = scene.minimumHeight()

    scene.set_disks([Disk(name, 10, 5) for name in "ABCDEF"])

    assert scene.minimumHeight() == one + 5 * 80
