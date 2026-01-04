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
Music media types package.

Contains Album, Track, Artist, and Playlist classes.
"""

from sok.media.music.album import Album
from sok.media.music.track import Track
from sok.media.music.artist import Artist
from sok.media.music.playlist import Playlist

__all__ = ["Album", "Track", "Artist", "Playlist"]
