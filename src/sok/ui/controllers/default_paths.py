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
"""Default destination folders configured in the settings."""

from pathlib import Path

from sok.config import get_config_manager

DEFAULT_PATH_KEYS = {
    "video": "default_video_path",
    "music": "default_music_path",
    "book": "default_books_path",
    "game": "default_games_path",
}


def default_destination(media_type: str) -> Path | None:
    """Return the default folder configured for a media type.

    Args:
        media_type: Type of media ('video', 'music', 'book', 'game').

    Returns:
        The configured folder, or None if unset or missing on disk.
    """
    key = DEFAULT_PATH_KEYS.get(media_type)
    value = get_config_manager().get(key, "") if key else ""
    if not value or not Path(value).is_dir():
        return None
    return Path(value)
