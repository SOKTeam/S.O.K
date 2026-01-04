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
Validation mixin for file operations.

Provides utilities to validate files and paths:
- Extension validation
- Path existence checking
- File retrieval by extension
"""

import os
from typing import List


class FileValidationMixin:
    """Mixin providing file validation utilities.

    Provides methods for validating file extensions, paths,
    and retrieving files by extension.
    """

    @staticmethod
    def is_valid_extension(filename: str, extensions: List[str]) -> bool:
        """Check if a file has a valid extension.

        Args:
            filename: File name.
            extensions: List of allowed extensions (with the dot).

        Returns:
            True if the extension is valid.
        """
        ext = os.path.splitext(filename)[1].lower()
        return ext in [e.lower() for e in extensions]

    @staticmethod
    def validate_path_exists(
        path: str, must_be_file: bool = False, must_be_dir: bool = False
    ) -> bool:
        """Validate that a path exists and matches the expected type.

        Args:
            path: Path to validate.
            must_be_file: Must be a file.
            must_be_dir: Must be a directory.

        Returns:
            True if the path is valid.
        """
        if not os.path.exists(path):
            return False
        if must_be_file and not os.path.isfile(path):
            return False
        if must_be_dir and not os.path.isdir(path):
            return False
        return True

    @staticmethod
    def get_files_by_extension(
        directory: str, extensions: List[str], recursive: bool = True
    ) -> List[str]:
        """Retrieve all files in a directory with the given extensions.

        Args:
            directory: Directory to scan.
            extensions: Extensions to search for.
            recursive: Enable recursive search.

        Returns:
            List of found file paths.
        """
        extensions_lower = [e.lower() for e in extensions]
        files: List[str] = []

        if recursive:
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    if os.path.splitext(filename)[1].lower() in extensions_lower:
                        files.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if (
                    os.path.isfile(filepath)
                    and os.path.splitext(filename)[1].lower() in extensions_lower
                ):
                    files.append(filepath)

        return files
