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
Music APIs package
"""

from sok.apis.music.spotify_api import SpotifyApi
from sok.apis.music.lastfm_api import LastFMApi
from sok.apis.music.deezer_api import DeezerApi

__all__ = ["SpotifyApi", "LastFMApi", "DeezerApi"]
