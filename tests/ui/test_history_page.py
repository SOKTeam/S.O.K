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

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from sok.core.history import Move, Operation, UndoReport, MISSING
from sok.ui import message_box
from sok.ui.controllers.undo import reason_text, undo_summary
from sok.ui.pages import history_page
from sok.ui.i18n import tr
from sok.ui.pages.history_page import HistoryPage, operation_title


def operation(op_id="a", undone=(False, False)):
    return Operation(
        id=op_id,
        date="2026-10-21T15:42:00",
        kind="movie",
        moves=[
            Move(f"/in/{i}.mkv", f"/out/Movie {i}.mkv", undone=done)
            for i, done in enumerate(undone)
        ],
    )


class ShownWindowSpy(QObject):
    """Record every top-level widget shown while installed."""

    def __init__(self):
        super().__init__()
        self.shown = []

    def eventFilter(self, obj, event):  # noqa: N802 - Qt API
        if (
            event.type() == QEvent.Type.Show
            and isinstance(obj, QWidget)
            and obj.isWindow()
        ):
            self.shown.append(type(obj).__name__)
        return False


def texts(widget):
    return [lbl.text() for lbl in widget.findChildren(QLabel)]


def test_the_page_lists_the_operations_newest_first(qtbot, rename_history):
    rename_history.add(operation("a"))
    rename_history.add(operation("b", undone=(True, True)))

    page = HistoryPage()
    qtbot.addWidget(page)

    assert [row.operation.id for row in page._rows] == ["b", "a"]
    assert page._current == "b"


def test_opening_the_history_shows_no_stray_window(qtbot, rename_history):
    # A key shown before it was in its line flashed as a window of its own
    # on Windows and Linux, at start and on each visit.
    rename_history.add(operation("a"))
    spy = ShownWindowSpy()
    app = QApplication.instance()
    app.installEventFilter(spy)
    try:
        page = HistoryPage()
        qtbot.addWidget(page)
        page.refresh()
    finally:
        app.removeEventFilter(spy)

    assert spy.shown == []


def test_an_empty_history_says_so(qtbot):
    page = HistoryPage()
    qtbot.addWidget(page)

    assert page._lead.text() == tr("history_empty", "No renames yet.")
    assert page._clear_btn.isHidden()
    assert page._scene_scroll.isHidden()


def test_the_scene_shows_the_files_of_the_rename_selected(qtbot, rename_history):
    rename_history.add(operation("a"))
    page = HistoryPage()
    qtbot.addWidget(page)

    page._select("a")

    assert "Movie 0.mkv" in texts(page._scene)
    assert any("0.mkv" in text and text != "Movie 0.mkv" for text in texts(page._scene))


def test_clearing_asks_first(qtbot, monkeypatch, rename_history):
    rename_history.add(operation())
    page = HistoryPage()
    qtbot.addWidget(page)
    monkeypatch.setattr(
        history_page.message_box,
        "question",
        lambda *args, **kwargs: message_box.StandardButton.Yes,
    )

    page._clear()

    assert rename_history.operations() == []
    assert page._rows == []


def test_the_title_counts_the_files_not_the_subtitles():
    op = operation()
    op.moves.append(Move("/in/0.srt", "/out/Movie 0.srt", follows="/out/Movie 0.mkv"))

    # The interface language is the one of the local settings.
    assert "2" in operation_title(op)
    assert "3" not in operation_title(op)


def test_the_undo_message_lists_the_files_left_in_place():
    move = Move("/in/a.mkv", "/out/A.mkv")
    report = UndoReport(restored=[Move("/in/b.mkv", "/out/B.mkv")])
    report.skipped.append((move, MISSING))

    text = undo_summary(report)

    assert "1" in text.splitlines()[0]
    assert f"• A.mkv — {reason_text(MISSING)}" in text


def test_a_batch_rename_gives_the_operation_to_undo(qtbot, tmp_path, rename_history):
    from sok.file_operations import BookFileOperations
    from sok.media.books.book import Book
    from sok.ui.workers.batch_worker import BatchOrganizeWorker

    source = tmp_path / "dune.epub"
    source.write_text("d")
    item = Book("Dune", "en", None, author="Frank Herbert")
    worker = BatchOrganizeWorker(
        [(source, item)],
        str(tmp_path / "out"),
        BookFileOperations().organize_items_batch,
    )
    reports = []
    worker.finished.connect(reports.append)

    worker.execute()

    operation_id = reports[0]["operation"]
    assert rename_history.get(operation_id).kind == "book"
    rename_history.undo(operation_id)
    assert source.read_text() == "d"


def test_posters_are_read_small_and_once(qtbot, tmp_path):
    from PySide6.QtGui import QColor, QImage

    path = tmp_path / "poster.jpg"
    image = QImage(1000, 1500, QImage.Format.Format_RGB32)
    image.fill(QColor(120, 60, 30))
    image.save(str(path))

    first = history_page.read_poster(str(path))

    assert first is not None
    assert first.height() == history_page.POSTER_HEIGHT
    assert history_page.read_poster(str(path)) is first
    assert history_page.read_poster(str(tmp_path / "gone.jpg")) is None


def test_the_whole_paths_show_under_the_mouse(qtbot, rename_history):
    rename_history.add(operation("a"))
    page = HistoryPage()
    qtbot.addWidget(page)
    page._select("a")
    sheet = page._scene._sheet
    labels = [label for label, _value in sheet._fields]

    from_row = labels.index(tr("history_field_from", "From"))
    to_row = labels.index(tr("history_field_to", "To"))

    assert sheet.tip_at(from_row * sheet.ROW + 5) == str(Path("/in"))
    assert sheet.tip_at(to_row * sheet.ROW + 5) == str(Path("/out"))
    assert (
        sheet.tip_at(
            labels.index(tr("history_field_transfer", "Transfer")) * sheet.ROW + 5
        )
        == ""
    )


def test_other_files_open_into_a_scrolling_list(qtbot):
    op = operation("a", undone=(False,) * 12)
    scene = history_page.HistoryScene()
    qtbot.addWidget(scene)
    scene.show_operation(op)
    assert len(scene._lines) == history_page.SHOWN_FILES
    assert not scene._more.isHidden()

    scene._more.clicked.emit()

    assert len(scene._lines) == 12
    assert scene._more.isHidden()
    line = scene._lines[0].sizeHint().height()
    assert scene._files_scroll.height() == line * history_page.OPEN_FILES_LINES
    # The 10th file puts back the 10th file, not one of the first four.
    undone = []
    scene.undo_file.connect(undone.append)
    scene._lines[9].button.click()
    assert undone == [9]


def test_another_rename_lists_its_first_files_only(qtbot):
    scene = history_page.HistoryScene()
    qtbot.addWidget(scene)
    scene.show_operation(operation("a", undone=(False,) * 12))
    scene._more.clicked.emit()

    scene.show_operation(operation("a", undone=(True,) + (False,) * 11))
    assert len(scene._lines) == 12

    scene.show_operation(operation("b", undone=(False,) * 12))
    assert len(scene._lines) == history_page.SHOWN_FILES


def test_one_file_left_over_is_listed(qtbot):
    scene = history_page.HistoryScene()
    qtbot.addWidget(scene)

    scene.show_operation(operation("a", undone=(False,) * 5))

    assert len(scene._lines) == 5
    assert scene._more.isHidden()
