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
"""TV series media adapter for API response normalization.

Normalizes search results and details from TV APIs (TMDB, TVDB)
into a consistent format.
"""

from __future__ import annotations

from typing import Any, Dict, List
from sok.core.interfaces import ContentType
from .base import BaseAdapter, _clean_str


class TvAdapter(BaseAdapter):
    """Adapter for normalizing TV series API responses."""

    def adapt_search(
        self, content_type: ContentType, results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Adapt TV series search results to normalized format.

        Args:
            content_type: Type of content (TV_SERIES, EPISODE).
            results: Raw API search results.

        Returns:
            Dictionary with 'results' key containing normalized TV series.
        """
        normalized = []
        for item in results:
            normalized.append(
                {
                    "id": item.get("id"),
                    "poster_path": item.get("poster_path") or item.get("image_url"),
                    "media_type": item.get("media_type") or "tv",
                    "name": _clean_str(item.get("name") or item.get("title")),
                    "original_name": _clean_str(
                        item.get("original_name") or item.get("original_title")
                    ),
                    "first_air_date": _clean_str(item.get("first_air_date")),
                }
            )
        return {"results": normalized}

    def adapt_details(
        self, content_type: ContentType, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt TV series detail response to normalized format.

        Args:
            content_type: Type of content (TV_SERIES, EPISODE).
            payload: Raw API detail response.

        Returns:
            Normalized TV series details dictionary.
        """
        data = dict(payload) if payload else {}
        data.setdefault("name", data.get("title"))
        data.setdefault("original_name", data.get("original_title") or data.get("name"))
        data.setdefault("first_air_date", _clean_str(data.get("first_air_date")))
        data.setdefault("seasons", data.get("seasons") or [])
        return data
