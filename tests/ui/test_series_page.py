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

from sok.ui.pages.series_page import group_by_series


def touch(folder: Path, *names: str) -> list[Path]:
    files = []
    for name in names:
        path = folder / name
        path.write_bytes(b"")
        files.append(path)
    return files


def test_episodes_are_grouped_by_series(tmp_path):
    files = touch(
        tmp_path,
        "Breaking.Bad.S01E01.mkv",
        "Breaking.Bad.S01E02.mkv",
        "Severance.S02E01.mkv",
    )

    items = group_by_series(files)

    assert sorted(len(item) for item in items) == [1, 2]
    assert {f.name for item in items for f in item} == {f.name for f in files}


def test_a_file_that_is_not_an_episode_is_alone(tmp_path):
    files = touch(tmp_path, "Breaking.Bad.S01E01.mkv", "holiday.mkv")

    items = group_by_series(files)

    assert sorted(len(item) for item in items) == [1, 1]


def test_each_series_is_organized_with_its_own_item(qtbot, monkeypatch):
    from sok.ui.pages.series_page import SeriesPage

    page = SeriesPage()
    qtbot.addWidget(page)
    calls = []

    def organize_files_list(files, dest, item, **kwargs):
        calls.append((item, list(files)))
        return {
            "moved": [{"from": str(f), "to": "x"} for f in files],
            "total_files": len(files),
            "total_moved": len(files),
        }

    monkeypatch.setattr(page._ops, "organize_files_list", organize_files_list)
    bb, sev = object(), object()
    mappings = [
        (Path("/a/bb1.mkv"), bb),
        (Path("/a/sev1.mkv"), sev),
        (Path("/a/bb2.mkv"), bb),
    ]

    report = page.organize_method()(mappings, "/dest")

    assert calls == [
        (bb, [Path("/a/bb1.mkv"), Path("/a/bb2.mkv")]),
        (sev, [Path("/a/sev1.mkv")]),
    ]
    assert report["total_moved"] == 3
    assert len(report["moved"]) == 3
