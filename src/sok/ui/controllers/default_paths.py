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
    "series": "default_series_path",
    "music": "default_music_path",
    "book": "default_books_path",
    "game": "default_games_path",
}


def default_destination(media_type: str) -> Path | None:
    """Return the default folder configured for a media type.

    Args:
        media_type: Type of media ('video', 'series', 'music', 'book',
            'game'). The TV shows go with the movies while their own
            folder is not set.

    Returns:
        The configured folder, or None if unset or missing on disk.
    """
    config = get_config_manager()
    key = DEFAULT_PATH_KEYS.get(media_type)
    value = config.get(key, "") if key else ""
    if not value and media_type == "series":
        value = config.get(DEFAULT_PATH_KEYS["video"], "")
    if not value or not Path(value).is_dir():
        return None
    return Path(value)
