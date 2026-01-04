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
Games APIs package.

Contains API implementations for video game metadata services:
- RAWG
- IGDB (Internet Game Database)
- Steam (limited)
"""

from sok.apis.games.rawg_api import RAWGApi
from sok.apis.games.igdb_api import IGDBApi

__all__ = ["RAWGApi", "IGDBApi"]
