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
Update system integration for the user interface.
Bridges the Core (UpdateManager) with the UI (UpdateDialog).
"""

import logging
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget
from sok.core.updater import UpdateManager
from sok.ui.dialogs.update_dialog import UpdateDialog
from sok.ui.controllers.worker_runner import WorkerRunner
import asyncio

logger = logging.getLogger(__name__)


class UpdateCheckWorker(QObject):
    """Worker thread to check for updates in the background.

    Signals:
        finished: Emitted with (found, version) when check completes.
        error: Emitted with error message on failure.
    """

    finished = Signal(bool, str)  # found, version
    error = Signal(str)

    def __init__(self, manager: UpdateManager):
        """Initialize the update check worker.

        Args:
            manager: Update manager instance.
        """
        super().__init__()
        self.manager = manager
        self._running = True

    def stop(self):
        """Stop the worker."""
        self._running = False

    def run(self):
        """Execute the update check."""

        try:
            if not self._running:
                return
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            found, version = loop.run_until_complete(self.manager.check_for_updates())
            if self._running:
                self.finished.emit(found, version or "")
        except (asyncio.CancelledError, RuntimeError, OSError, ValueError) as e:
            logger.exception("Update check failed", exc_info=e)
            self.error.emit(str(e))
        finally:
            try:
                loop.close()
            except (RuntimeError, OSError) as exc:
                logger.debug("Loop close failed", exc_info=exc)


def check_and_show_updates(parent_widget: QWidget):
    """Launch update check and display dialog if necessary.

    This function is non-blocking. It checks for updates in a
    background thread and shows the update dialog if an update
    is available.

    Args:
        parent_widget: Parent widget for the update dialog.
    """
    manager = UpdateManager()

    worker = UpdateCheckWorker(manager)

    def on_check_finished(found: bool, version: str):
        """Handle update check completion.

        Args:
            found: Whether an update was found.
            version: New version string if found.
        """
        if found:
            dialog = UpdateDialog(parent_widget, manager, version)
            dialog.exec()

    runner = getattr(parent_widget, "_update_runner", None)
    if runner is None:
        runner = WorkerRunner(parent_widget)
        if parent_widget:
            setattr(parent_widget, "_update_runner", runner)

    runner.run(
        worker, on_check_finished, lambda e: logger.error("Update check error: %s", e)
    )
