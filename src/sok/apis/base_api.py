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
"""Base API client implementation.

Provides the foundational BaseAPI class that all media API clients inherit from.
Handles HTTP session management, request lifecycle, and connection pooling.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional
from sok.core.interfaces import MediaAPI


class BaseAPI(MediaAPI):
    """Common base class for all API implementations.

    Provides shared functionality for HTTP requests, session management,
    and connection handling. All specific API implementations should
    inherit from this class.

    Attributes:
        api_key: API authentication key.
        base_url: Base URL for API requests.
    """

    def __init__(self, api_key: str, base_url: str):
        """Initialize the API client.

        Args:
            api_key: API authentication key.
            base_url: Base URL for all API requests.
        """
        self.api_key: str = api_key
        self.base_url: str = base_url
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_loop: Optional[object] = None

    @property
    def session(self) -> Optional[aiohttp.ClientSession]:
        """Get the HTTP session.

        Returns:
            The aiohttp ClientSession if valid for current event loop, None otherwise.
        """
        return self._session

    @session.setter
    def session(self, value: Optional[aiohttp.ClientSession]) -> None:
        """Set the HTTP session.

        Args:
            value: The aiohttp ClientSession to use, or None to clear.
        """
        self._session = value
        if value is not None:
            try:
                self._session_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._session_loop = None

    def _is_session_valid(self) -> bool:
        """Check if the current session is valid for the running event loop.

        Returns:
            True if session exists, is not closed, and belongs to current loop.
        """
        if self._session is None or self._session.closed:
            return False
        try:
            current_loop = asyncio.get_running_loop()
            return self._session_loop is current_loop
        except RuntimeError:
            return False

    async def __aenter__(self) -> "BaseAPI":
        """Enter async context manager.

        Creates a new aiohttp session bound to the current event loop.

        Returns:
            Self for use in async with statement.
        """
        self._session = aiohttp.ClientSession()
        self._session_loop = asyncio.get_running_loop()
        return self

    async def __aexit__(self, *args) -> None:
        """Exit async context manager.

        Closes the aiohttp session and cleans up resources.
        """
        if self._session:
            await self._session.close()
            self._session = None
            self._session_loop = None

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
        data: Optional[str] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request to the API.

        Automatically manages session lifecycle and handles event loop changes.

        Args:
            endpoint: API endpoint path (appended to base_url).
            params: Query parameters.
            headers: HTTP headers.
            method: HTTP method ('GET' or 'POST').
            data: Raw string data for POST requests.
            json_data: JSON data for POST requests.

        Returns:
            Parsed JSON response as dictionary.
        """
        if not self._is_session_valid():
            if self._session and not self._session.closed:
                try:
                    await self._session.close()
                except Exception:
                    pass
            self._session = aiohttp.ClientSession()
            self._session_loop = asyncio.get_running_loop()

        if params is None:
            params = {}

        url = f"{self.base_url}{endpoint}"

        session = self._session
        assert session is not None

        if method.upper() == "POST":
            async with session.post(
                url, params=params, headers=headers, data=data, json=json_data
            ) as response:
                return await response.json()
        else:
            async with session.get(url, params=params, headers=headers) as response:
                return await response.json()

    async def close(self) -> None:
        """Close the aiohttp session.

        Safe to call multiple times. Errors during close are silently ignored.
        """
        if self._session:
            try:
                await self._session.close()
            except Exception:
                pass
            self._session = None
            self._session_loop = None
