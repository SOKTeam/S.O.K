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
"""Adapters for normalizing API responses.

Contains media adapters that transform raw API responses
into consistent formats for each media type.
"""

from sok.core.adapters.media_adapters import adapt_search_results, adapt_details

__all__ = ["adapt_search_results", "adapt_details"]
