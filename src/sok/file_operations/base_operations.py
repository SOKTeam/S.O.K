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
Base operations common to all media types.

This module provides the BaseFileOperations class that combines
parsing and validation mixins with concrete file operations:
- Hash calculation
- Duplicate detection
- Safe move/copy
- Batch renaming
- Backup creation
"""

import os
import hashlib
import shutil
import logging
from typing import List, Dict, Any, Optional, Callable

from .mixins import (
    FileParsingMixin,
    FileValidationMixin,
    VIDEO_QUALITY_PATTERNS,
    VIDEO_CODECS,
    AUDIO_CODECS,
    CONTENT_SOURCES,
    LANGUAGE_PATTERNS,
    INVALID_FILENAME_CHARS,
)


logger = logging.getLogger(__name__)

__all__ = [
    "BaseFileOperations",
    "FileParsingMixin",
    "FileValidationMixin",
    "VIDEO_QUALITY_PATTERNS",
    "VIDEO_CODECS",
    "AUDIO_CODECS",
    "CONTENT_SOURCES",
    "LANGUAGE_PATTERNS",
    "INVALID_FILENAME_CHARS",
]


class BaseFileOperations(FileParsingMixin, FileValidationMixin):
    """Base class with common utilities for file operations.

    Provides static methods for hash calculation, duplicate detection,
    safe file operations, and batch processing.
    """

    @staticmethod
    def calculate_file_hash(
        file_path: str, algorithm: str = "md5", chunk_size: int = 8192
    ) -> str:
        """Calculate the hash of a file.

        Args:
            file_path: Path to the file.
            algorithm: Hash algorithm ('md5', 'sha1', 'sha256').
            chunk_size: Chunk size for reading in bytes.

        Returns:
            File hash in hexadecimal, or empty string on error.
        """
        hash_obj = hashlib.new(algorithm)

        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    hash_obj.update(chunk)

            return hash_obj.hexdigest()
        except OSError as exc:
            logger.exception("Hash calculation failed for %s", file_path, exc_info=exc)
            return ""

    @staticmethod
    def find_duplicates(
        directory: str,
        extensions: List[str],
        recursive: bool = True,
        by_hash: bool = True,
        by_size: bool = False,
    ) -> Dict[str, List[str]]:
        """Find duplicate files in a directory.

        Args:
            directory: Directory path to analyze.
            extensions: File extensions to consider.
            recursive: Whether to search recursively.
            by_hash: Compare by file hash (more accurate).
            by_size: Compare by file size (faster).

        Returns:
            Dictionary mapping keys to lists of duplicate file paths.
        """
        files_map: Dict[str, List[str]] = {}

        files_to_check = []
        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions):
                        files_to_check.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                if any(file.lower().endswith(ext) for ext in extensions):
                    files_to_check.append(os.path.join(directory, file))

        for file_path in files_to_check:
            try:
                if by_hash:
                    key = BaseFileOperations.calculate_file_hash(file_path)
                elif by_size:
                    key = str(os.path.getsize(file_path))
                else:
                    key = os.path.basename(file_path).lower()

                if key:
                    if key not in files_map:
                        files_map[key] = []
                    files_map[key].append(file_path)

            except OSError as exc:
                logger.exception(
                    "Duplicate scan failed for %s", file_path, exc_info=exc
                )

        duplicates = {k: v for k, v in files_map.items() if len(v) > 1}

        return duplicates

    @staticmethod
    def safe_move(
        source: str, destination: str, overwrite: bool = False, create_dirs: bool = True
    ) -> bool:
        """Move a file safely.

        Args:
            source: Source file path.
            destination: Destination file path.
            overwrite: Whether to overwrite existing files.
            create_dirs: Whether to create parent directories.

        Returns:
            True if successful, False otherwise.
        """
        try:
            if not os.path.exists(source):
                logger.warning("Source file does not exist: %s", source)
                return False

            if create_dirs:
                dest_dir = os.path.dirname(destination)
                if dest_dir:
                    os.makedirs(dest_dir, exist_ok=True)

            if os.path.exists(destination):
                if not overwrite:
                    logger.warning("Destination already exists: %s", destination)
                    return False
                else:
                    backup = f"{destination}.backup"
                    if os.path.exists(backup):
                        os.remove(backup)
                    shutil.move(destination, backup)

            shutil.move(source, destination)
            return True

        except OSError as exc:
            logger.exception(
                "Safe move failed from %s to %s", source, destination, exc_info=exc
            )
            return False

    @staticmethod
    def safe_copy(
        source: str, destination: str, overwrite: bool = False, create_dirs: bool = True
    ) -> bool:
        """Copy a file safely.

        Args:
            source: Source file path.
            destination: Destination file path.
            overwrite: Whether to overwrite existing files.
            create_dirs: Whether to create parent directories.

        Returns:
            True if successful, False otherwise.
        """
        try:
            if not os.path.exists(source):
                logger.warning("Source file does not exist: %s", source)
                return False

            if create_dirs:
                dest_dir = os.path.dirname(destination)
                if dest_dir:
                    os.makedirs(dest_dir, exist_ok=True)

            if os.path.exists(destination) and not overwrite:
                logger.warning("Destination already exists: %s", destination)
                return False

            shutil.copy2(source, destination)
            return True

        except OSError as exc:
            logger.exception(
                "Safe copy failed from %s to %s", source, destination, exc_info=exc
            )
            return False

    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """Retrieve file information.

        Args:
            file_path: Path to the file.

        Returns:
            Dictionary with file metadata (size, dates, etc.).
        """
        info: Dict[str, Any] = {
            "path": file_path,
            "name": os.path.basename(file_path),
            "size": 0,
            "size_mb": 0.0,
            "size_gb": 0.0,
            "extension": "",
            "exists": False,
            "is_file": False,
            "is_dir": False,
            "created": None,
            "modified": None,
            "accessed": None,
        }

        try:
            if os.path.exists(file_path):
                info["exists"] = True
                info["is_file"] = os.path.isfile(file_path)
                info["is_dir"] = os.path.isdir(file_path)

                if info["is_file"]:
                    stat = os.stat(file_path)
                    info["size"] = stat.st_size
                    info["size_mb"] = round(stat.st_size / (1024 * 1024), 2)
                    info["size_gb"] = round(stat.st_size / (1024 * 1024 * 1024), 2)
                    info["extension"] = os.path.splitext(file_path)[1]
                    info["created"] = stat.st_ctime
                    info["modified"] = stat.st_mtime
                    info["accessed"] = stat.st_atime

        except OSError as exc:
            logger.exception("File info failed for %s", file_path, exc_info=exc)

        return info

    @staticmethod
    def clean_filename(filename: str, replace_char: str = "_") -> str:
        """Clean a filename by removing invalid characters.

        Args:
            filename: Filename to clean.
            replace_char: Character to replace invalid chars with.

        Returns:
            Cleaned filename safe for file systems.
        """
        invalid_chars = '<>:"/\\|?*'

        cleaned = filename
        for char in invalid_chars:
            cleaned = cleaned.replace(char, replace_char)

        cleaned = cleaned.strip()

        name, ext = os.path.splitext(cleaned)
        name = name.rstrip(".")
        cleaned = name + ext

        return cleaned

    @staticmethod
    def format_size(size_bytes: float) -> str:
        """Format a size in bytes to human readable format.

        Args:
            size_bytes: Size in bytes.

        Returns:
            Formatted size string (e.g., '1.5 GB').
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    @staticmethod
    def get_directory_size(directory: str) -> int:
        """Calculate the total size of a directory.

        Args:
            directory: Directory path to analyze.

        Returns:
            Total size in bytes.
        """
        total_size = 0

        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        except OSError as exc:
            logger.exception(
                "Directory size calculation failed for %s", directory, exc_info=exc
            )

        return total_size

    @staticmethod
    def batch_rename(
        files: List[str], rename_function: Callable[[str], str], dry_run: bool = False
    ) -> Dict[str, Any]:
        """Rename multiple files using a rename function.

        Args:
            files: List of file paths to rename.
            rename_function: Function that takes old name and returns new name.
            dry_run: If True, simulate without renaming.

        Returns:
            Report dictionary with total, renamed, errors, skipped lists.
        """
        report: Dict[str, Any] = {
            "total": len(files),
            "renamed": [],
            "errors": [],
            "skipped": [],
        }

        for file_path in files:
            try:
                directory = os.path.dirname(file_path)
                old_name = os.path.basename(file_path)
                new_name = rename_function(old_name)

                if old_name == new_name:
                    report["skipped"].append(file_path)
                    continue

                new_path = os.path.join(directory, new_name)

                if os.path.exists(new_path):
                    report["errors"].append(
                        {
                            "file": file_path,
                            "error": f"Destination already exists: {new_path}",
                        }
                    )
                    continue

                if not dry_run:
                    os.rename(file_path, new_path)

                report["renamed"].append({"from": file_path, "to": new_path})

            except OSError as exc:
                logger.exception("Batch rename failed for %s", file_path, exc_info=exc)
                report["errors"].append({"file": file_path, "error": str(exc)})

        return report

    @staticmethod
    def create_backup(
        file_path: str, backup_dir: Optional[str] = None
    ) -> Optional[str]:
        """Create a backup of a file.

        Args:
            file_path: Path to the file to backup.
            backup_dir: Backup folder path (None = same directory).

        Returns:
            Created backup path, or None on error.
        """
        try:
            if not os.path.exists(file_path):
                return None

            if backup_dir:
                os.makedirs(backup_dir, exist_ok=True)
                backup_name = os.path.basename(file_path)
                backup_path = os.path.join(backup_dir, f"{backup_name}.backup")
            else:
                backup_path = f"{file_path}.backup"

            counter = 1
            original_backup_path = backup_path
            while os.path.exists(backup_path):
                if backup_dir:
                    backup_name = os.path.basename(file_path)
                    backup_path = os.path.join(
                        backup_dir, f"{backup_name}.backup.{counter}"
                    )
                else:
                    backup_path = f"{original_backup_path}.{counter}"
                counter += 1

            shutil.copy2(file_path, backup_path)
            return backup_path

        except OSError as exc:
            logger.exception("Backup creation failed for %s", file_path, exc_info=exc)
            return None
