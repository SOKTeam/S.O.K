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
from typing import Optional


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger with a null handler to avoid "No handler" warnings if not configured."""
    logger = logging.getLogger(name if name else __name__)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def format_name(name: str) -> str:
    """Formats a filename by removing forbidden characters"""
    return re.sub(" +", " ", re.sub(r'[<>:"/\\|?*]', "", name))


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
