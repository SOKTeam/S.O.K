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

from typing import Any, Callable, Dict, List

from sok.core.batch import parse_book, same_book
from sok.core.interfaces import ContentType, MediaType
from sok.file_operations import BookFileOperations
from sok.ui.i18n import tr
from sok.ui.components.scene import Shape
from sok.ui.components.file_row import RowData
from sok.ui.components.organize.media_list import Entry
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

    kind = "books"
    scene_shape = Shape.BOOK
    show_found_in = False
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

    def query_placeholder(self) -> str:
        return tr("book_title_author", "Title (optional author)")

    def lead_prefix(self, entries: List[Entry]) -> List[str]:
        return [tr("batch_books_by_author", "Filed by author.")] if entries else []

    def _row_data(self, entry: Entry) -> RowData:
        """A book: its spine at the left, the author, the format as a tag."""
        data = super()._row_data(entry)
        data.book = True
        data.by_tone = "ink-muted"
        data.year = ""
        formats = sorted(
            {f.suffix.lstrip(".").upper() for f in entry.files if f.suffix}
        )
        data.tags = formats[:1]
        return data
