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
Video APIs Module for S.O.K

This module contains all API implementations for video media
(movies, TV series, documentaries, etc.)

Available APIs:
- TMDBApi: The Movie Database (movies + series)
- TVDBApi: TheTVDB (specialized TV series)
- IMDBApi: IMDb via OMDb (movies + series with IMDb ratings)
"""

from sok.apis.video.tmdb_api import TMDBApi
from sok.apis.video.tvdb_api import TVDBApi
from sok.apis.video.imdb_api import IMDBApi

__all__ = ["TMDBApi", "TVDBApi", "IMDBApi"]
