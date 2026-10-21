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

from sok.core.adapters.media_adapters import adapt_search_results
from sok.core.interfaces import ContentType
from sok.file_operations import BookFileOperations
from sok.media.books.book import Book
from sok.ui.factories.media_factory import create_media_item


def test_adapter_splits_the_authors_string_of_the_apis():
    adapted = adapt_search_results(
        ContentType.BOOK,
        [{"id": 1, "title": "Dune", "author": "Frank Herbert, Brian Herbert"}],
    )
    assert adapted["results"][0]["authors"] == ["Frank Herbert", "Brian Herbert"]


def test_factory_keeps_author_and_year():
    book = create_media_item(
        {
            "id": 1,
            "title": "Dune",
            "authors": ["Frank Herbert"],
            "published_date": "1965",
        },
        "book",
        manager=None,
    )
    assert isinstance(book, Book)
    assert book.get_formatted_name() == "Frank Herbert - Dune (1965)"
    assert book.get_folder_structure() == [
        "Frank Herbert",
        "Frank Herbert - Dune (1965)",
    ]


def test_book_is_named_after_the_online_book():
    book = Book("Dune", "en", None, author="Frank Herbert")
    book.published_date = "1965-08-01"
    ops = BookFileOperations()

    assert (
        ops.generate_new_filename(book, "dune_v2.EPUB")
        == "Frank Herbert - Dune (1965).epub"
    )


def test_batch_moves_each_book_to_its_own_folder(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    dune, foundation = src / "dune.epub", src / "found.pdf"
    dune.write_text("d")
    foundation.write_text("f")
    first = Book("Dune", "en", None, author="Frank Herbert")
    second = Book("Foundation", "en", None, author="Isaac Asimov")
    second.published_date = "1951"

    report = BookFileOperations().organize_items_batch(
        [(dune, first), (foundation, second)], str(tmp_path / "out")
    )

    assert report["total_moved"] == 2
    assert (
        tmp_path / "out/Frank Herbert/Frank Herbert - Dune/Frank Herbert - Dune.epub"
    ).exists()
    assert (
        tmp_path
        / "out/Isaac Asimov/Isaac Asimov - Foundation (1951)/Isaac Asimov - Foundation (1951).pdf"
    ).exists()
    assert not Path(dune).exists()
