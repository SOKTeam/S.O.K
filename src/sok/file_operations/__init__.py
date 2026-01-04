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
File operations management module for different media types.

This module provides classes to handle file operations
for each media type (video, music, books, games).
"""

from sok.file_operations.base_operations import (
    BaseFileOperations,
    FileParsingMixin,
    FileValidationMixin,
    VIDEO_QUALITY_PATTERNS,
    VIDEO_CODECS,
    AUDIO_CODECS,
    CONTENT_SOURCES,
    LANGUAGE_PATTERNS,
    INVALID_FILENAME_CHARS,
)
from sok.file_operations.video_operations import VideoFileOperations
from sok.file_operations.music_operations import MusicFileOperations
from sok.file_operations.book_operations import BookFileOperations
from sok.file_operations.game_operations import GameFileOperations

__all__ = [
    "BaseFileOperations",
    "FileParsingMixin",
    "FileValidationMixin",
    "VideoFileOperations",
    "MusicFileOperations",
    "BookFileOperations",
    "GameFileOperations",
    "VIDEO_QUALITY_PATTERNS",
    "VIDEO_CODECS",
    "AUDIO_CODECS",
    "CONTENT_SOURCES",
    "LANGUAGE_PATTERNS",
    "INVALID_FILENAME_CHARS",
]
