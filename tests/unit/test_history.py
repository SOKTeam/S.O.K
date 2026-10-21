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
from sok.core.history import (
    MAX_OPERATIONS,
    MISSING,
    OCCUPIED,
    HistoryStore,
    Operation,
    current_journal,
    record,
)
from sok.file_operations import BookFileOperations
from sok.file_operations.base_operations import make_folders, move_file
from sok.media.books.book import Book


def rename_books(tmp_path, *names):
    """Rename books from tmp/in to tmp/out inside record(); return the journal."""
    src = tmp_path / "in"
    src.mkdir(exist_ok=True)
    mappings = []
    for name in names:
        path = src / f"{name.lower()}.epub"
        path.write_text(name)
        mappings.append((path, Book(name, "en", None, author="Frank Herbert")))
    with record("book") as journal:
        BookFileOperations().organize_items_batch(mappings, str(tmp_path / "out"))
    return journal


def test_a_rename_is_recorded_with_its_moves_and_folders(tmp_path, rename_history):
    journal = rename_books(tmp_path, "Dune")

    operation = rename_history.get(journal.operation_id)
    assert operation.kind == "book"
    assert [m.source for m in operation.moves] == [str(tmp_path / "in/dune.epub")]
    assert operation.moves[0].target.endswith("Frank Herbert - Dune.epub")
    # out/, out/Frank Herbert/, out/Frank Herbert/Frank Herbert - Dune/
    assert len(operation.folders) == 3


def test_nothing_is_recorded_when_nothing_moved(rename_history):
    with record("movie") as journal:
        pass

    assert journal.operation_id is None
    assert rename_history.operations() == []


def test_undo_puts_the_files_back_and_removes_the_new_folders(tmp_path, rename_history):
    journal = rename_books(tmp_path, "Dune", "Children")

    report = rename_history.undo(journal.operation_id)

    assert len(report.restored) == 2
    assert (tmp_path / "in/dune.epub").read_text() == "Dune"
    assert (tmp_path / "in/children.epub").exists()
    assert not (tmp_path / "out").exists()
    assert rename_history.get(journal.operation_id).undone


def test_a_folder_with_only_system_files_is_removed(tmp_path, rename_history):
    journal = rename_books(tmp_path, "Dune")
    (tmp_path / "out/Frank Herbert/.DS_Store").write_bytes(b"")

    rename_history.undo(journal.operation_id)

    assert not (tmp_path / "out").exists()


def test_undo_of_one_file_leaves_the_others(tmp_path, rename_history):
    journal = rename_books(tmp_path, "Dune", "Children")
    operation = rename_history.get(journal.operation_id)

    rename_history.undo(journal.operation_id, 0)

    assert (tmp_path / "in/dune.epub").exists()
    assert not (tmp_path / "in/children.epub").exists()
    assert operation.partly_undone
    # The author folder still holds the other book.
    assert (tmp_path / "out/Frank Herbert").exists()


def test_undo_never_replaces_a_file(tmp_path, rename_history):
    journal = rename_books(tmp_path, "Dune", "Children")
    operation = rename_history.get(journal.operation_id)
    dune, children = operation.moves
    (tmp_path / "in/dune.epub").write_text("a new file")
    (tmp_path / "out/moved-away.epub").write_bytes(b"")
    move_file(children.target, str(tmp_path / "out/moved-away.epub"))

    report = rename_history.undo(journal.operation_id)

    assert sorted(reason for _, reason in report.skipped) == [MISSING, OCCUPIED]
    assert (tmp_path / "in/dune.epub").read_text() == "a new file"
    assert not operation.undone


def test_undo_puts_back_the_replaced_file(tmp_path, rename_history):
    old, new = tmp_path / "old.mkv", tmp_path / "new.mkv"
    old.write_text("old")
    new.write_text("new")
    with record("movie") as journal:
        move_file(str(new), str(old), backup=True)
    assert old.read_text() == "new"

    rename_history.undo(journal.operation_id)

    assert new.read_text() == "new"
    assert old.read_text() == "old"
    assert not (tmp_path / "old.mkv.backup").exists()


def test_a_poster_is_deleted_once_all_its_files_are_back(tmp_path, rename_history):
    folder = tmp_path / "Show"
    folder.mkdir()
    files = []
    with record("tv_series") as journal:
        for name in ["e1.mkv", "e2.mkv"]:
            (tmp_path / name).write_bytes(b"")
            move_file(str(tmp_path / name), str(folder / name))
            files.append(str(folder / name))
        (folder / "poster.jpg").write_bytes(b"")
        current_journal().saved_artwork(str(folder / "poster.jpg"), files)

    rename_history.undo(journal.operation_id, 0)
    assert (folder / "poster.jpg").exists()

    rename_history.undo(journal.operation_id, 1)
    assert not (folder / "poster.jpg").exists()


def test_make_folders_reports_only_the_folders_it_creates(tmp_path):
    (tmp_path / "a").mkdir()
    with record("movie") as journal:
        make_folders(str(tmp_path / "a/b/c"))

    assert journal.folders == [str(tmp_path / "a/b/c"), str(tmp_path / "a/b")]


def test_the_history_is_saved_and_read_back(tmp_path, rename_history):
    journal = rename_books(tmp_path, "Dune")
    rename_history.undo(journal.operation_id)

    again = HistoryStore(rename_history.path).get(journal.operation_id)

    assert again == rename_history.get(journal.operation_id)
    assert again.undone


def test_only_the_last_operations_are_kept(tmp_path):
    store = HistoryStore(tmp_path / "history.json")
    for i in range(MAX_OPERATIONS + 5):
        store.add(Operation(id=str(i), date="2026-10-21T12:00:00", kind="movie"))

    ids = [op.id for op in store.operations()]
    assert len(ids) == MAX_OPERATIONS
    assert ids[0] == str(MAX_OPERATIONS + 4)


def test_an_unreadable_history_starts_empty(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("{not json")

    assert HistoryStore(path).operations() == []


def test_clear_empties_the_history(tmp_path, rename_history):
    rename_books(tmp_path, "Dune")

    rename_history.clear()

    assert rename_history.operations() == []
    assert HistoryStore(rename_history.path).operations() == []
