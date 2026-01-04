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
"""Game media adapter for API response normalization.

Normalizes search results and details from game APIs (IGDB, RAWG)
into a consistent format.
"""

from __future__ import annotations

from typing import Any, Dict, List
from sok.core.interfaces import ContentType
from .base import BaseAdapter, _clean_str


class GameAdapter(BaseAdapter):
    """Adapter for normalizing game API responses."""

    def adapt_search(
        self, content_type: ContentType, results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Adapt game search results to normalized format.

        Args:
            content_type: Type of content (GAME).
            results: Raw API search results.

        Returns:
            Dictionary with 'results' key containing normalized games.
        """
        normalized = []
        for item in results:
            normalized.append(
                {
                    "id": item.get("id"),
                    "poster_path": item.get("poster_path") or item.get("image_url"),
                    "media_type": item.get("media_type") or content_type.value,
                    "title": _clean_str(item.get("title") or item.get("name")),
                    "platform": _clean_str(item.get("platform")),
                    "release_date": _clean_str(item.get("release_date")),
                }
            )
        return {"results": normalized}

    def adapt_details(
        self, content_type: ContentType, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt game detail response to normalized format.

        Args:
            content_type: Type of content (GAME).
            payload: Raw API detail response.

        Returns:
            Normalized game details dictionary.
        """
        data = dict(payload) if payload else {}
        data.setdefault("title", data.get("name"))
        data.setdefault("platforms", data.get("platforms") or [])
        data.setdefault("release_date", _clean_str(data.get("release_date")))
        return data
