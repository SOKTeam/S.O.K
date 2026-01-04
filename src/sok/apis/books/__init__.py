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
Books APIs package.

Contains API implementations for book metadata services:
- Google Books
- Open Library
- Goodreads (deprecated)
"""

from sok.apis.books.google_books_api import GoogleBooksApi
from sok.apis.books.open_library_api import OpenLibraryApi

__all__ = ["GoogleBooksApi", "OpenLibraryApi"]
