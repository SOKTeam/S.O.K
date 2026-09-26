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
from sok.ui.components.inputs import DropZone

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


def apply_default_destination(drop_zone: DropZone, media_type: str) -> None:
    """Fill an empty destination drop zone with the default folder.

    Args:
        drop_zone: Destination drop zone.
        media_type: Type of media ('video', 'music', 'book', 'game').
    """
    if drop_zone.get_path() is not None:
        return
    path = default_destination(media_type)
    if path is not None:
        drop_zone.set_path(path)
