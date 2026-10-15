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

import re
from pathlib import Path
from typing import Iterable, List


def natural_key(path: Path) -> list:
    """Sort key that orders numbers by value: "S01E2" before "S01E10".

    Args:
        path: File path, compared case-insensitively.
    """
    return [
        int(part) if part.isdigit() else part
        for part in re.split(r"(\d+)", str(path).casefold())
    ]


def scan_sources(ops, paths: Iterable[Path]) -> List[Path]:
    """Return all matching files for provided paths using the ops helpers.

    Uses the unified `find_files` method if available,
    otherwise falls back to type-specific methods. Files keep the order of
    the source folders and are sorted naturally within each folder: the
    file system lists them in no particular order.
    """
    files: list[Path] = []
    seen = set()
    for path in paths:
        path_str = str(path)
        found: list = []

        if hasattr(ops, "find_files"):
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
