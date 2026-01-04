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
Base Worker definitions for S.O.K
"""

import asyncio
import logging
from typing import Optional
from PySide6.QtCore import QObject, Signal
from sok.config.config_manager import ConfigManager, get_config_manager

logger = logging.getLogger(__name__)


class BaseWorker(QObject):
    """Abstract base worker for async operations in QThread.

    Manages asyncio event loop lifecycle and provides error handling.
    Subclasses must implement the execute() method.

    Signals:
        error (str): Emitted when execution fails.

    Attributes:
        _config: Application configuration manager.
        _loop: Asyncio event loop for the worker thread.
    """

    error = Signal(str)

    def __init__(self, config: Optional[ConfigManager] = None):
        """Initialize the base worker.

        Args:
            config: Configuration manager (uses default if None).
        """
        super().__init__()
        self._config = config or get_config_manager()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def run(self):
        """Execute the worker in a new event loop.

        Creates an async event loop, runs execute(), and ensures cleanup.
        Emits error signal on failure.
        """
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            try:
                self.execute()
            finally:
                self._loop.close()
        except (asyncio.CancelledError, RuntimeError, OSError) as exc:
            logger.exception("Worker execution failed", exc_info=exc)
            self.error.emit(str(exc))

    def execute(self):
        """Execute worker logic (must be implemented by subclasses).

        Use self._loop.run_until_complete() for async operations.

        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError("Subclasses must implement execute()")
