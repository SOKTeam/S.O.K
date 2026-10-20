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
"""Page for batch-renaming books, each with its own online book."""

from typing import Any, Callable, Dict

from sok.core.batch import parse_book, same_book
from sok.core.interfaces import ContentType, MediaType
from sok.file_operations import BookFileOperations
from sok.ui.i18n import tr
from sok.ui.pages.batch_page import BatchPage


def describe_book(candidate: Dict[str, Any]) -> str:
    """ "Title — Author (year)", the text of a book in the menu of a row."""
    title = candidate.get("title") or tr("unknown", "Unknown")
    authors = ", ".join(candidate.get("authors") or [])
    year = str(candidate.get("published_date") or "")[:4]
    text = f"{title} — {authors}" if authors else title
    return f"{text} ({year})" if year.isdigit() else text


class BooksPage(BatchPage):
    """Page for batch book renaming.

    Each book goes to Author/Author - Title (Year)/, under the name
    "Author - Title (Year)". The editions of a book count as one match.
    """

    default_path_type = "book"
    media_type = MediaType.BOOK
    content_type = ContentType.BOOK
    factory_type = "book"
    parse = staticmethod(parse_book)
    same_work = staticmethod(same_book)
    # The language of the app would hide books written in other languages.
    localized = False
    describe = staticmethod(describe_book)

    def make_ops(self) -> BookFileOperations:
        return BookFileOperations()

    def organize_method(self) -> Callable[..., Dict[str, Any]]:
        return self._ops.organize_items_batch

    def page_title(self) -> str:
        return tr("books", "Books")

    def empty_hint(self) -> str:
        return tr("books_drop_hint", "Drop book files or folders, or click to browse")

    def add_more_text(self) -> str:
        return tr("add_more_books", "+ Add more books")

    def query_placeholder(self) -> str:
        return tr("book_title_author", "Title (optional author)")
