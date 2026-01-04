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
"""Music media adapter for API response normalization.

Normalizes search results and details from music APIs (Spotify, Deezer,
MusicBrainz) into a consistent format.
"""

from __future__ import annotations

from typing import Any, Dict, List
from sok.core.interfaces import ContentType
from .base import BaseAdapter, _clean_str


class MusicAdapter(BaseAdapter):
    """Adapter for normalizing music API responses."""

    def adapt_search(
        self, content_type: ContentType, results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Adapt music search results to normalized format.

        Args:
            content_type: Type of content (ALBUM, TRACK, ARTIST).
            results: Raw API search results.

        Returns:
            Dictionary with 'results' key containing normalized music items.
        """
        normalized = []
        for item in results:
            normalized.append(
                {
                    "id": item.get("id"),
                    "poster_path": item.get("poster_path") or item.get("image_url"),
                    "media_type": item.get("media_type") or content_type.value,
                    "title": _clean_str(item.get("title") or item.get("name")),
                    "artist": _clean_str(item.get("artist")),
                    "release_date": _clean_str(item.get("release_date")),
                }
            )
        return {"results": normalized}

    def adapt_details(
        self, content_type: ContentType, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt music detail response to normalized format.

        Args:
            content_type: Type of content (ALBUM, TRACK, ARTIST).
            payload: Raw API detail response.

        Returns:
            Normalized music details dictionary.
        """
        data = dict(payload) if payload else {}
        data.setdefault("title", data.get("name"))
        data.setdefault("artist", data.get("artist"))
        data.setdefault("release_date", _clean_str(data.get("release_date")))
        data.setdefault("tracks", data.get("tracks") or [])
        return data
