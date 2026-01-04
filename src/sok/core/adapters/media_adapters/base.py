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
"""Base adapter classes for API response normalization.

Provides the abstract Adapter protocol and BaseAdapter class that
all media-type-specific adapters inherit from.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol
from sok.core.interfaces import ContentType


class Adapter(Protocol):
    """Protocol defining the adapter interface.

    All media adapters must implement these methods to normalize
    API responses into a consistent format.
    """

    def adapt_search(
        self, content_type: ContentType, results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Adapt search results to normalized format.

        Args:
            content_type: Type of content being searched.
            results: Raw API search results.

        Returns:
            Normalized search results dictionary.
        """
        ...

    def adapt_details(
        self, content_type: ContentType, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt detail response to normalized format.

        Args:
            content_type: Type of content.
            payload: Raw API detail response.

        Returns:
            Normalized detail dictionary.
        """
        ...


def _clean_str(value: Optional[str]) -> Optional[str]:
    """Clean and normalize a string value.

    Args:
        value: String to clean, or None.

    Returns:
        Stripped string if non-empty, None otherwise.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


class BaseAdapter:
    """Base class for media adapters.

    Provides default implementations that raise NotImplementedError,
    forcing subclasses to implement the required methods.
    """

    def adapt_search(
        self, content_type: ContentType, results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Adapt search results to normalized format.

        Args:
            content_type: Type of content being searched.
            results: Raw API search results.

        Returns:
            Normalized search results dictionary.

        Raises:
            NotImplementedError: Must be implemented by subclass.
        """
        raise NotImplementedError

    def adapt_details(
        self, content_type: ContentType, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adapt detail response to normalized format.

        Args:
            content_type: Type of content.
            payload: Raw API detail response.

        Returns:
            Normalized detail dictionary.

        Raises:
            NotImplementedError: Must be implemented by subclass.
        """
        raise NotImplementedError
