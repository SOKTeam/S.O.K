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

from sok.core.batch import STATUS_AMBIGUOUS, STATUS_READY, BatchMatch
from sok.ui.components.organize.media_batch_table import MediaBatchTable

DUNE = [
    {"title": "Dune : Troisième partie", "release_date": "2026-12-16"},
    {"title": "Dune", "release_date": "2021-09-15"},
]


class TestMediaBatchTableDrop:
    def test_dropped_folder_is_scanned(self, qtbot, tmp_path):
        (tmp_path / "Movies" / "Sub").mkdir(parents=True)
        (tmp_path / "Movies" / "b.mkv").write_text("")
        (tmp_path / "Movies" / "Sub" / "a.MP4").write_text("")
        (tmp_path / "Movies" / "notes.txt").write_text("")
        loose = tmp_path / "c.mkv"
        loose.write_text("")
        table = MediaBatchTable([".mkv", ".mp4"])
        qtbot.addWidget(table)

        found = table._filter_supported([tmp_path / "Movies", loose])

        assert sorted(p.name for p in found) == ["a.MP4", "b.mkv", "c.mkv"]


def table_with(qtbot, *matches):
    table = MediaBatchTable([".mkv"])
    qtbot.addWidget(table)
    table.set_files([m.file for m in matches])
    table.apply_results(list(matches))
    return table


class TestMediaBatchTableStatus:
    def test_only_ready_rows_are_renamed(self, qtbot):
        ready = BatchMatch(
            [Path("/a/Dune.2021.mkv")], "Dune", 2021, DUNE, 1, STATUS_READY
        )
        to_pick = BatchMatch(
            [Path("/a/Dune.mkv")], "Dune", None, DUNE, 0, STATUS_AMBIGUOUS
        )
        table = table_with(qtbot, ready, to_pick)

        assert table.get_ready_mappings() == [([ready.file], DUNE[1])]
        assert table.count_by_status()[STATUS_AMBIGUOUS] == 1

    def test_choosing_the_selected_candidate_confirms_it(self, qtbot):
        to_pick = BatchMatch(
            [Path("/a/Dune.mkv")], "Dune", None, DUNE, 1, STATUS_AMBIGUOUS
        )
        table = table_with(qtbot, to_pick)
        row = table._rows[to_pick.file]

        row._match_combo.activated.emit(1)

        assert table.get_ready_mappings() == [([to_pick.file], DUNE[1])]

    def test_renamed_rows_are_removed_and_the_others_stay(self, qtbot):
        ready = BatchMatch(
            [Path("/a/Dune.2021.mkv")], "Dune", 2021, DUNE, 1, STATUS_READY
        )
        to_pick = BatchMatch(
            [Path("/a/Dune.mkv")], "Dune", None, DUNE, 0, STATUS_AMBIGUOUS
        )
        table = table_with(qtbot, ready, to_pick)

        table.remove_files([ready.file])

        assert table.files() == [to_pick.file]
        table.remove_files([to_pick.file])
        assert not table.has_rows()


def by_stem(files):
    groups = {}
    for f in files:
        groups.setdefault(f.with_suffix(""), []).append(f)
    return list(groups.values())


class TestMediaBatchTableItems:
    def test_files_of_an_item_share_one_row(self, qtbot):
        table = MediaBatchTable([".cue", ".bin"], group_files=by_stem)
        qtbot.addWidget(table)
        cue, bin_, iso = Path("/g/Crash.cue"), Path("/g/Crash.bin"), Path("/g/Halo.cue")

        items = table.add_files([cue, bin_, iso])

        assert items == [[cue, bin_], [iso]]
        assert table.items() == [[cue, bin_], [iso]]
        assert table.add_files([bin_]) == []

    def test_a_ready_item_maps_all_its_files(self, qtbot):
        table = MediaBatchTable([".cue", ".bin"], group_files=by_stem)
        qtbot.addWidget(table)
        cue, bin_ = Path("/g/Crash.cue"), Path("/g/Crash.bin")
        table.add_files([cue, bin_])
        game = {"title": "Crash Bandicoot", "release_date": "1996-09-09"}

        table.apply_search_result(
            BatchMatch([cue, bin_], "Crash", None, [game], 0, STATUS_READY)
        )

        assert table.get_ready_mappings() == [([cue, bin_], game)]

    def test_removing_one_file_removes_its_whole_row(self, qtbot):
        table = MediaBatchTable([".cue", ".bin"], group_files=by_stem)
        qtbot.addWidget(table)
        cue, bin_ = Path("/g/Crash.cue"), Path("/g/Crash.bin")
        table.add_files([cue, bin_])

        table.remove_files([bin_])

        assert table.files() == []
        assert not table.has_rows()
