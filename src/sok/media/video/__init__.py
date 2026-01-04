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
Video media types package.

Contains Movie, Series, and Episode classes.
"""

from sok.media.video.movie import Movie
from sok.media.video.series import Series
from sok.media.video.episode import Episode

__all__ = ["Movie", "Series", "Episode"]
