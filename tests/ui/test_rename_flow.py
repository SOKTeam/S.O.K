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
"""The rename of a media page: the list follows it, then shows the end."""

from pathlib import Path

import pytest

from sok.core.batch import STATUS_MISSING, STATUS_READY, BatchMatch
from sok.core.history import current_journal
from sok.ui.components.organize.media_list import STATUS_DONE, STATUS_OK
from sok.ui.pages.batch_page import duration_text
from sok.ui.pages.movies_page import MoviesPage
from sok.ui.workers.batch_worker import BatchOrganizeWorker


class _Item:
    content_type = None


def fake_organize(stop_after=None):
    """An organize method that "moves" each file and records it."""

    def organize(mappings, dest_path, dry_run=False, progress_callback=None):
        moved = []
        for index, (file, _item) in enumerate(mappings):
            if progress_callback:
                progress_callback(index + 1, len(mappings), file.name)
            target = str(Path(dest_path) / file.name)
            current_journal().moved(str(file), target, None)
            moved.append({"from": str(file), "to": target})
        return {
            "total_files": len(mappings),
            "total_moved": len(moved),
            "moved": moved,
            "errors": [],
            "skipped": [],
        }

    return organize


class TestWorker:
    def run(self, worker):
        reports, started = [], []
        worker.finished.connect(reports.append)
        worker.file_started.connect(lambda name, n, total: started.append(name))
        worker.execute()
        return reports[0], started

    def test_each_file_is_announced_before_it_moves(self, tmp_path):
        files = [tmp_path / "a.mkv", tmp_path / "b.mkv"]
        worker = BatchOrganizeWorker(
            [(f, _Item()) for f in files], str(tmp_path / "dest"), fake_organize()
        )

        report, started = self.run(worker)

        assert started == ["a.mkv", "b.mkv"]
        assert report["success"] == 2
        assert report["stopped"] is False

    def test_a_stop_ends_between_two_files_and_keeps_what_moved(self, tmp_path):
        files = [tmp_path / "a.mkv", tmp_path / "b.mkv", tmp_path / "c.mkv"]
        worker = BatchOrganizeWorker(
            [(f, _Item()) for f in files], str(tmp_path / "dest"), fake_organize()
        )
        worker.file_started.connect(
            lambda name, n, total: worker.request_stop() if n == 1 else None
        )

        report, started = self.run(worker)

        assert started == ["a.mkv"]
        assert report["stopped"] is True
        assert [m["from"] for m in report["moved"]] == [str(files[0])]
        assert report["operation"]  # saved in the history, so it can be undone


@pytest.fixture
def page(qtbot, tmp_path):
    src, dest = tmp_path / "src", tmp_path / "dest"
    src.mkdir()
    dest.mkdir()
    names = ["Dune.2021.mkv", "Heat.1995.mkv", "DSC_0012.mp4"]
    for name in names:
        (src / name).write_bytes(b"x" * 10)
    widget = MoviesPage()
    qtbot.addWidget(widget)
    widget._dest_drop.set_path(dest)
    files = [src / n for n in names]
    widget._list.add_files(files)
    results = []
    for f in files:
        if f.name.startswith("DSC"):
            results.append(BatchMatch([f], f.stem, None, [], None, STATUS_MISSING))
        else:
            title, year = f.stem.split(".")
            cand = [{"id": 1, "title": title, "release_date": f"{year}-01-01"}]
            results.append(BatchMatch([f], title, int(year), cand, 0, STATUS_READY))
    widget._on_batch_search_done(results)
    runs = []
    widget._organize_runner.run = lambda *args, **kwargs: runs.append(args)
    # No search on the internet: without API keys (the CI), it fails and
    # shows a modal warning that nobody closes.
    widget._search_runner.run = lambda *args, **kwargs: None
    widget.runs = runs
    widget.files = files
    widget.dest = dest
    return widget


class TestPage:
    def test_the_click_starts_at_once_and_lists_what_waits(self, page):
        page._start_rename()

        assert page.runs  # no question asked first
        phases = {e.files[0].name: e.phase for e in page._list.entries()}
        assert phases == {
            "Dune.2021.mkv": "waiting",
            "Heat.1995.mkv": "waiting",
            "DSC_0012.mp4": "stays",
        }
        assert not page._stop_btn.isHidden()
        assert page._action_btn.isHidden()

    def test_the_list_follows_each_file(self, page):
        page._start_rename()

        page._on_file_started("Dune.2021.mkv", 1, 2)
        page._on_file_started("Heat.1995.mkv", 2, 2)

        dune, heat = page._list.entries()[:2]
        assert dune.phase == "done"
        assert heat.phase == "current"
        assert page._run_lbl.text().startswith("1 / 2")

    def test_stop_asks_the_worker_to_stop(self, page):
        page._start_rename()
        stops = []
        page._run.worker.request_stop = lambda: stops.append(1)

        page._stop_rename()

        assert stops == [1]

    def test_the_end_shows_each_item_and_what_is_left(self, page):
        dune, heat, dsc = page.files
        page._start_rename()

        page._on_organize_done(
            {
                "success": 1,
                "moved": [
                    {"from": str(dune), "to": str(page.dest / "Dune (2021).mkv")}
                ],
                "errors": [{"file": str(heat), "error": "[Errno 16] Resource busy"}],
                "skipped": [],
                "operation": "op",
            }
        )

        entries = {e.files[0].name: e for e in page._list.entries()}
        assert entries["Dune.2021.mkv"].status == STATUS_DONE
        assert entries["Dune.2021.mkv"].moved_to == "dest/Dune (2021).mkv"
        assert entries["Heat.1995.mkv"].phase == "failed"
        assert entries["Heat.1995.mkv"].reason == "Resource busy"
        assert entries["DSC_0012.mp4"].phase == "stays"
        # What is left comes first, the sorted items after.
        order = [e.files[0].name for e in page._list.entries()]
        assert order[-1] == "Dune.2021.mkv"
        assert page._right.currentWidget() is page._summary_scroll
        # The failed one is ready again, behind a key that is not primary.
        assert not page._action_btn.isHidden()
        assert not page._action_btn._primary

    def test_new_files_after_the_end_clear_the_sorted_items(self, page, tmp_path):
        dune = page.files[0]
        page._start_rename()
        page._on_organize_done(
            {
                "success": 1,
                "moved": [{"from": str(dune), "to": str(page.dest / "x.mkv")}],
                "errors": [],
                "skipped": [],
                "operation": "op",
            }
        )
        new = tmp_path / "src" / "Alien.1979.mkv"
        new.write_bytes(b"x")

        page._list.add_files([new])
        page._on_files_added([[new]])

        names = [e.files[0].name for e in page._list.entries()]
        assert "Dune.2021.mkv" not in names
        assert page._phase == "idle"
        assert all(e.phase == "" for e in page._list.entries())
        assert any(e.status == STATUS_OK for e in page._list.entries())


def test_scrolling_the_right_column_moves_its_light(page):
    lights = []
    page.light_changed.connect(lambda: lights.append(1))

    for scroll in (page._scene_scroll, page._summary_scroll):
        bar = scroll.verticalScrollBar()
        bar.setRange(0, 100)
        bar.setValue(10)

    assert len(lights) >= 2


def test_durations():
    assert duration_text(38) == "38 s"
    assert duration_text(130) == "2 min 10"


class TestMotion:
    def test_a_sorted_row_draws_its_check(self, qtbot):
        from sok.ui.components.file_row import FileRow, RowData

        row = FileRow(RowData("Dune", phase="waiting"))
        qtbot.addWidget(row)

        row.set_data(RowData("Dune", phase="done"))

        assert row._sorted < 1.0
        qtbot.waitUntil(lambda: row._sorted == 1.0, timeout=1000)

    def test_the_gauge_fills_when_recognized(self, qtbot):
        from sok.ui.components.file_row import FileRow, RowData

        row = FileRow(RowData("Dune"))
        qtbot.addWidget(row)

        row.set_data(RowData("Dune", confidence=5))

        assert row._gauge < 5
        qtbot.waitUntil(lambda: row._gauge == 5.0, timeout=1000)

    def test_a_crossfade_swaps_at_once_and_fades_the_old_view(self, qtbot):
        from PySide6.QtWidgets import QLabel, QStackedWidget

        from sok.ui.motion import crossfade

        stack = QStackedWidget()
        qtbot.addWidget(stack)
        first, second = QLabel("first"), QLabel("second")
        stack.addWidget(first)
        stack.addWidget(second)
        stack.resize(200, 100)
        stack.show()
        steps = []

        crossfade(stack, lambda: stack.setCurrentWidget(second), 60, steps.append)

        # The new view is there at once; the old one is a picture over it.
        assert stack.currentWidget() is second
        pictures = [w for w in stack.findChildren(QLabel) if w.pixmap() is not None]
        pictures = [w for w in pictures if not w.pixmap().isNull()]
        assert len(pictures) == 1
        qtbot.waitUntil(lambda: bool(steps) and steps[-1] == 1.0, timeout=1000)
        qtbot.waitUntil(lambda: pictures[0] not in stack.findChildren(QLabel))

    def test_a_hidden_place_changes_without_a_fade(self, qtbot):
        from PySide6.QtWidgets import QLabel, QStackedWidget

        from sok.ui.motion import crossfade

        stack = QStackedWidget()
        qtbot.addWidget(stack)
        second = QLabel("second")
        stack.addWidget(QLabel("first"))
        stack.addWidget(second)
        steps = []

        crossfade(stack, lambda: stack.setCurrentWidget(second), 60, steps.append)

        assert stack.currentWidget() is second
        assert steps == []

    def test_a_flight_goes_away_and_calls_back_when_landed(self, qtbot):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QWidget

        from sok.ui.motion import _Flight, fly

        host = QWidget()
        qtbot.addWidget(host)
        host.resize(300, 200)
        landed = []
        pixmap = QPixmap(20, 30)

        fly(
            host,
            pixmap,
            QRectF(0, 0, 20, 30),
            QRectF(200, 100, 40, 60),
            60,
            on_done=lambda: landed.append(1),
        )

        assert len(host.findChildren(_Flight)) == 1
        qtbot.waitUntil(lambda: landed == [1], timeout=1000)
        qtbot.waitUntil(lambda: not host.findChildren(_Flight), timeout=1000)

    def test_rise_skips_what_is_hidden_on_purpose_only(self, qtbot):
        from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

        from sok.ui.motion import cascade

        host = QWidget()
        qtbot.addWidget(host)
        layout = QVBoxLayout(host)
        host.show()
        hidden, fresh = QLabel("hidden"), QLabel("fresh")
        layout.addWidget(hidden)
        hidden.hide()
        layout.addWidget(fresh)  # Qt shows it a moment later

        cascade([hidden, fresh])

        assert hidden.graphicsEffect() is None
        assert fresh.graphicsEffect() is not None

    def test_the_scene_is_whole_again_after_a_choice(self, page):
        dune = next(
            e for e in page._list.entries() if e.files[0].name.startswith("Dune")
        )
        page._list.set_current(dune.key)
        page._open_picker()

        page._on_picker_chosen(0)

        assert page._right.currentWidget() is page._scene_scroll
        assert not page._scene._stage.object_hidden
