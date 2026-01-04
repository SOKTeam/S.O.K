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
OAuth Handler - Manages external service authentication via Qt

This module provides a Qt interface to launch OAuth authentications
using centralized providers from sok.config.oauth_providers.
"""

import logging
from PySide6.QtCore import QObject, Signal
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.config.oauth_providers import get_oauth_provider

logger = logging.getLogger(__name__)


class OAuthWorker(QObject):
    """Worker for OAuth authentication.

    Delegates to centralized providers from sok.config.oauth_providers.

    Signals:
        finished: Emitted when authentication completes (with result or None).
        success: Emitted with credentials dict on success.
        error: Emitted with error message on failure.
    """

    finished = Signal(object)
    success = Signal(dict)
    error = Signal(str)

    def __init__(self, service: str, api_key: str = "", api_secret: str = ""):
        """Initialize the OAuth worker.

        Args:
            service: Service name (e.g., 'lastfm', 'discogs').
            api_key: API key for the service.
            api_secret: API secret for the service.
        """
        super().__init__()
        self.service = service
        self.api_key = api_key
        self.api_secret = api_secret
        self._running = True

    def stop(self):
        """Stop the worker."""
        self._running = False

    def run(self):
        """Execute the OAuth flow via centralized providers."""
        if not self._running:
            return
        try:
            provider = get_oauth_provider(self.service, self.api_key, self.api_secret)

            if not provider:
                self.error.emit(f"Unknown service: {self.service}")
                self.finished.emit(None)
                return

            result = provider.authenticate()

            if self._running and result:
                self.success.emit(result)
                self.finished.emit(result)
            else:
                self.error.emit("Authentication cancelled")
                self.finished.emit(None)

        except (ImportError, ValueError, RuntimeError) as e:
            logger.exception(
                "OAuth flow failed for service %s", self.service, exc_info=e
            )
            self.error.emit(str(e))
            self.finished.emit(None)


class OAuthManager(QObject):
    """OAuth manager for Qt interface.

    Manages OAuth authentication flows with background workers.

    Signals:
        auth_success: Emitted with (service, data) on success.
        auth_error: Emitted with (service, error) on failure.
        auth_started: Emitted with service name when auth starts.
    """

    auth_success = Signal(str, dict)
    auth_error = Signal(str, str)
    auth_started = Signal(str)

    def __init__(self):
        """Initialize the OAuth manager."""
        super().__init__()
        self._runner = WorkerRunner(self)

    def authenticate(self, service: str, api_key: str = "", api_secret: str = ""):
        """Launch authentication for a service.

        Args:
            service: Service name (e.g., 'lastfm', 'discogs').
            api_key: API key for the service.
            api_secret: API secret for the service.
        """
        self.auth_started.emit(service)
        worker = OAuthWorker(service, api_key, api_secret)
        self._runner.run(
            worker,
            lambda data: self._on_success(service, data) if data is not None else None,
            lambda err: self._on_error(service, err),
        )

    def _on_success(self, service: str, data: dict):
        """Handle authentication success.

        Args:
            service: Service that authenticated.
            data: Authentication credentials.
        """
        self.auth_success.emit(service, data)

    def _on_error(self, service: str, error: str):
        """Handle authentication error.

        Args:
            service: Service that failed.
            error: Error message.
        """
        self.auth_error.emit(service, error)
