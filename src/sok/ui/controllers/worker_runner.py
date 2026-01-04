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
"""Utility to run PySide6 workers in a QThread safely."""

import logging
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QMessageBox, QWidget
from sok.ui.i18n import tr

logger = logging.getLogger(__name__)


class WorkerRunner:
    """Utility to run PySide6 workers in a QThread safely.

    Manages worker lifecycle, signal connections, and error handling
    for background tasks.
    """

    def __init__(self, parent=None):
        """Initialize the worker runner.

        Args:
            parent: Parent widget for thread ownership.
        """
        self._thread: QThread | None = None
        self._current_worker = None
        self._parent = parent

    def stop(self):
        """Stop the current worker and thread."""
        try:
            if self._thread and self._thread.isRunning():
                if self._current_worker and hasattr(self._current_worker, "stop"):
                    try:
                        self._current_worker.stop()
                    except (RuntimeError, AttributeError) as exc:
                        logger.exception("Worker stop() failed", exc_info=exc)
                self._thread.quit()
                self._thread.wait()
        except RuntimeError:
            pass
        self._thread = None
        self._current_worker = None

    def run(self, worker, on_finished, on_error, on_progress=None):
        """Run a worker in a background thread.

        Args:
            worker: Worker object with run(), finished, and error signals.
            on_finished: Callback for finished signal.
            on_error: Callback for error signal.
            on_progress: Optional callback for progress signal.

        Returns:
            The worker object.
        """
        self.stop()

        self._current_worker = worker
        self._thread = QThread(self._parent)
        worker.moveToThread(self._thread)

        if hasattr(self._thread, "started") and hasattr(worker, "run"):
            self._thread.started.connect(worker.run)
        if hasattr(worker, "finished"):
            worker.finished.connect(on_finished)
            worker.finished.connect(self._thread.quit)
        if hasattr(worker, "error"):

            def _handle_error(err):
                """Handle worker error signal.

                Args:
                    err: Error message from worker.
                """
                if on_error:
                    on_error(err)
                self._show_error(err)

            worker.error.connect(_handle_error)
            worker.error.connect(self._thread.quit)
        if on_progress and hasattr(worker, "progress"):
            worker.progress.connect(on_progress)

        self._thread.finished.connect(worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_refs)

        self._thread.start()
        return worker

    def _clear_refs(self):
        """Clear thread and worker references."""
        self._thread = None
        self._current_worker = None

    def _show_error(self, err):
        """Show error message to user.

        Args:
            err: Error message or exception.
        """
        parent = self._parent if isinstance(self._parent, QWidget) else None
        if not parent:
            return
        message = str(err) if err else tr("unknown_error", "An error occurred")

        if hasattr(parent, "statusBar") and callable(parent.statusBar):
            status = parent.statusBar()
            if status:
                status.showMessage(message, 8000)
                return

        QMessageBox.critical(
            parent,
            tr("task_failed", "Task failed"),
            message,
        )
