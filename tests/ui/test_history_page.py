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
from PySide6.QtWidgets import QLabel

from sok.core.history import Move, Operation, UndoReport, MISSING
from sok.ui import message_box
from sok.ui.controllers.undo import reason_text, undo_summary
from sok.ui.pages import history_page
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


def texts(widget):
    return [lbl.text() for lbl in widget.findChildren(QLabel)]


def test_the_page_lists_the_operations(qtbot, rename_history):
    rename_history.add(operation("a"))
    rename_history.add(operation("b", undone=(True, True)))

    page = HistoryPage()
    qtbot.addWidget(page)

    assert [card._operation.id for card in page._cards] == ["b", "a"]
    assert page._empty.isHidden()


def test_an_empty_history_says_so(qtbot):
    page = HistoryPage()
    qtbot.addWidget(page)

    assert not page._empty.isHidden()
    assert page._clear_btn.isHidden()


def test_a_card_shows_its_files_when_clicked(qtbot, rename_history):
    rename_history.add(operation())
    page = HistoryPage()
    qtbot.addWidget(page)
    card = page._cards[0]

    card._toggle()

    assert any("0.mkv  →  Movie 0.mkv" in text for text in texts(card))
    assert card._chevron.text() == "⌄"


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
    assert page._cards == []


def test_the_title_counts_the_files():
    # The interface language is the one of the local settings.
    assert "2" in operation_title(operation()).split(" · ")[1]


def test_the_title_counts_the_subtitles_apart():
    op = operation()
    op.moves.append(Move("/in/0.srt", "/out/Movie 0.srt", follows="/out/Movie 0.mkv"))

    parts = operation_title(op).split(" · ")

    assert len(parts) == 3
    assert "2" in parts[1]
    assert "1" in parts[2]


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
