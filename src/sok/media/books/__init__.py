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
"""
Books media types package.

Contains Book, Ebook, Audiobook, and Comic classes.
"""

from sok.media.books.book import Book
from sok.media.books.ebook import Ebook
from sok.media.books.audiobook import Audiobook
from sok.media.books.comic import Comic

__all__ = ["Book", "Ebook", "Audiobook", "Comic"]
