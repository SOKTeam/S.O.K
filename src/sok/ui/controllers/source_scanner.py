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
"""Helpers to scan source folders using available file operation methods."""

from pathlib import Path
from typing import Iterable, List

from sok.core.utils import natural_key


def scan_sources(ops, paths: Iterable[Path]) -> List[Path]:
    """Return all matching files for provided paths using the ops helpers.

    A path can be a file, kept if the ops support its extension, or a folder.
    Folders use the unified `find_files` method if available,
    otherwise fall back to type-specific methods. Files keep the order of
    the source folders and are sorted naturally within each folder: the
    file system lists them in no particular order.
    """
    files: list[Path] = []
    seen = set()
    for path in paths:
        path_str = str(path)
        found: list = []

        if path.is_file():
            extensions = getattr(ops, "supported_extensions", None)
            if extensions is None or path.suffix.lower() in extensions:
                found = [path_str]
        elif hasattr(ops, "find_files"):
            found = ops.find_files(path_str)
        elif hasattr(ops, "find_video_files"):
            found = ops.find_video_files(path_str)
        elif hasattr(ops, "find_audio_files"):
            found = ops.find_audio_files(path_str)
        elif hasattr(ops, "find_book_files"):
            found = ops.find_book_files(path_str)
        elif hasattr(ops, "find_game_files"):
            found = ops.find_game_files(path_str)
        elif hasattr(ops, "supported_extensions"):
            for ext in ops.supported_extensions:
                found.extend(path.rglob(f"*{ext}"))

        for f in sorted(found, key=lambda f: natural_key(Path(f))):
            pf = Path(f)
            if pf not in seen:
                seen.add(pf)
                files.append(pf)
    return files
