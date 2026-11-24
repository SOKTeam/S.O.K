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
from sok.ui.components.file_row import RowData
from sok.ui.components.organize.media_list import Entry, MediaList

DUNE = [
    {"title": "Dune : Troisième partie", "release_date": "2026-12-16"},
    {"title": "Dune", "release_date": "2021-09-15"},
]


def make_row(entry: Entry) -> RowData:
    return RowData(entry.query, entry.files[0].name, confidence=entry.confidence)


def new_list(qtbot, extensions=(".mkv",), **kwargs) -> MediaList:
    media = MediaList(make_row, list(extensions), **kwargs)
    qtbot.addWidget(media)
    return media


def list_with(qtbot, *matches) -> MediaList:
    media = new_list(qtbot)
    media.set_files([m.file for m in matches])
    media.apply_results(list(matches))
    return media


def test_dropped_folder_is_scanned(qtbot, tmp_path):
    (tmp_path / "Movies" / "Sub").mkdir(parents=True)
    (tmp_path / "Movies" / "b.mkv").write_text("")
    (tmp_path / "Movies" / "Sub" / "a.MP4").write_text("")
    (tmp_path / "Movies" / "notes.txt").write_text("")
    loose = tmp_path / "c.mkv"
    loose.write_text("")
    media = new_list(qtbot, (".mkv", ".mp4"))

    found = media.filter_supported([tmp_path / "Movies", loose])

    assert sorted(p.name for p in found) == ["a.MP4", "b.mkv", "c.mkv"]


class TestStatus:
    def test_only_ready_items_are_renamed(self, qtbot):
        ready = BatchMatch(
            [Path("/a/Dune.2021.mkv")], "Dune", 2021, DUNE, 1, STATUS_READY
        )
        to_pick = BatchMatch(
            [Path("/a/Dune.mkv")], "Dune", None, DUNE, 0, STATUS_AMBIGUOUS
        )
        media = list_with(qtbot, ready, to_pick)

        assert media.get_ready_mappings() == [([ready.file], DUNE[1])]
        assert media.count_by_status()[STATUS_AMBIGUOUS] == 1

    def test_choosing_a_candidate_confirms_it(self, qtbot):
        to_pick = BatchMatch(
            [Path("/a/Dune.mkv")], "Dune", None, DUNE, 0, STATUS_AMBIGUOUS
        )
        media = list_with(qtbot, to_pick)

        media.choose(to_pick.file, 1)

        assert media.get_ready_mappings() == [([to_pick.file], DUNE[1])]

    def test_gauge_follows_the_status(self, qtbot):
        with_year = BatchMatch(
            [Path("/a/Dune.2021.mkv")], "Dune", 2021, DUNE, 1, STATUS_READY
        )
        title_only = BatchMatch(
            [Path("/a/Dune.mkv")], "Dune", None, DUNE, 1, STATUS_READY
        )
        to_pick = BatchMatch([Path("/a/X.mkv")], "X", None, DUNE, 0, STATUS_AMBIGUOUS)
        missing = BatchMatch([Path("/a/Y.mkv")], "Y", None, [], None, "missing")
        media = list_with(qtbot, with_year, title_only, to_pick, missing)

        assert [e.confidence for e in media.entries()] == [5, 4, 2, 0]

    def test_items_still_searching_become_missing_after_a_failed_search(self, qtbot):
        media = new_list(qtbot)
        media.add_files([Path("/a/Dune.mkv")])
        media.set_row_loading(Path("/a/Dune.mkv"))

        media.fail_pending()

        assert media.count_by_status()["missing"] == 1

    def test_a_search_is_asked_for_the_item(self, qtbot):
        media = new_list(qtbot)
        media.add_files([Path("/a/Dune.mkv")])
        asked = []
        media.row_rescan_requested.connect(
            lambda key, query: asked.append((key, query))
        )

        media.request_search(Path("/a/Dune.mkv"), "  Dune 2021 ")
        media.request_search(Path("/a/Dune.mkv"), "   ")

        assert asked == [(Path("/a/Dune.mkv"), "Dune 2021")]


class TestSelection:
    def test_the_first_item_is_selected(self, qtbot):
        media = new_list(qtbot)

        media.add_files([Path("/a/A.mkv"), Path("/a/B.mkv")])

        assert media.current() == Path("/a/A.mkv")

    def test_removing_the_selected_item_selects_the_next_one(self, qtbot):
        media = new_list(qtbot)
        media.add_files([Path("/a/A.mkv"), Path("/a/B.mkv"), Path("/a/C.mkv")])
        media.set_current(Path("/a/B.mkv"))

        media.remove_files([Path("/a/B.mkv")])

        assert media.current() == Path("/a/C.mkv")
        media.remove_files([Path("/a/A.mkv"), Path("/a/C.mkv")])
        assert media.current() is None
        assert not media.has_rows()

    def test_select_next_stops_at_the_ends(self, qtbot):
        media = new_list(qtbot)
        media.add_files([Path("/a/A.mkv"), Path("/a/B.mkv")])

        media.select_next()
        media.select_next()

        assert media.current() == Path("/a/B.mkv")
        media.select_next(-1)
        assert media.current() == Path("/a/A.mkv")


def by_stem(files):
    groups = {}
    for f in files:
        groups.setdefault(f.with_suffix(""), []).append(f)
    return list(groups.values())


class TestItems:
    def test_files_of_an_item_share_one_row(self, qtbot):
        media = new_list(qtbot, (".cue", ".bin"), group_files=by_stem)
        cue, bin_, iso = Path("/g/Crash.cue"), Path("/g/Crash.bin"), Path("/g/Halo.cue")

        items = media.add_files([cue, bin_, iso])

        assert items == [[cue, bin_], [iso]]
        assert media.items() == [[cue, bin_], [iso]]
        assert media.add_files([bin_]) == []

    def test_a_ready_item_maps_all_its_files(self, qtbot):
        media = new_list(qtbot, (".cue", ".bin"), group_files=by_stem)
        cue, bin_ = Path("/g/Crash.cue"), Path("/g/Crash.bin")
        media.add_files([cue, bin_])
        game = {"title": "Crash Bandicoot", "release_date": "1996-09-09"}

        media.apply_search_result(
            BatchMatch([cue, bin_], "Crash", None, [game], 0, STATUS_READY)
        )

        assert media.get_ready_mappings() == [([cue, bin_], game)]

    def test_removing_one_file_removes_its_whole_row(self, qtbot):
        media = new_list(qtbot, (".cue", ".bin"), group_files=by_stem)
        cue, bin_ = Path("/g/Crash.cue"), Path("/g/Crash.bin")
        media.add_files([cue, bin_])

        media.remove_files([bin_])

        assert media.files() == []
        assert not media.has_rows()
