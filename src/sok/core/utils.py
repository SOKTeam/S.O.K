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
"""General utility functions.

Provides common utility functions for filename formatting, episode
information extraction, file type detection, and logging setup.
"""

import re
import os
import logging
from pathlib import Path
from typing import Optional


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger with a null handler to avoid "No handler" warnings if not configured."""
    logger = logging.getLogger(name if name else __name__)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def natural_key(path: Path) -> list:
    """Sort key that orders numbers by value: "S01E2" before "S01E10".

    Args:
        path: File path, compared case-insensitively.
    """
    return [
        int(part) if part.isdigit() else part
        for part in re.split(r"(\d+)", str(path).casefold())
    ]


def format_name(name: str) -> str:
    """Formats a file or folder name: no forbidden character, single spaces,
    and no dot or space at the end of the name or before its extension.

    A title that ends with "..." no longer gives "Bag....mkv", and a folder
    no longer ends with a dot, which Windows refuses.
    """
    name = re.sub(" +", " ", re.sub(r'[<>:"/\\|?*]', "", name))
    name = re.sub(r"[ .]+(\.[A-Za-z0-9]{1,5})$", r"\1", name)
    return name.rstrip(" .")


class _Missing(dict):
    """Values for str.format_map: an unknown field gives ""."""

    def __missing__(self, key: str) -> str:
        return ""


def fill_format(fmt: str, values: dict[str, str]) -> str:
    """Fill a name format of the settings, such as "{author} - {title} ({year})".

    A value that is empty or unknown is left out with what it leaves around
    it: without a year, the example gives "Author - Title".

    Args:
        fmt: The format, with {field} placeholders.
        values: The value of each field.

    Returns:
        The filled text, or "" if the format is not valid ("{", "{0}"…).
    """
    try:
        text = fmt.format_map(_Missing(values))
    except (ValueError, IndexError, AttributeError, TypeError):
        return ""
    text = re.sub(r"\(\s*\)|\[\s*\]", "", text)
    text = re.sub(r"\s*-\s*(?:-\s*)+", " - ", text)
    text = re.sub(r"^[\s\-_.]+|[\s\-_.]+$", "", text)
    return re.sub(r"\s{2,}", " ", text)


def extract_episode_info(filename: str) -> Optional[dict]:
    """Extracts episode information from a filename"""
    match = re.search(
        r"(?P<name>.*)S(?P<season>\d+)E(?P<episode>\d+)(?P<rest>.*)", filename
    )
    if match:
        return {
            "name": match.group("name").strip(),
            "season": int(match.group("season")),
            "episode": int(match.group("episode")),
            "rest": match.group("rest"),
        }
    return None


def is_video_file(filename: str) -> bool:
    """Checks if a file is a video file"""
    video_extensions = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"}
    return os.path.splitext(filename)[1].lower() in video_extensions
