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
from PySide6.QtCore import QObject, QThread
from PySide6.QtWidgets import QWidget
from sok.ui.i18n import tr
from sok.ui import message_box

logger = logging.getLogger(__name__)


class _GuiCallback(QObject):
    """Run a callback in the thread that created it (the GUI thread).

    A signal connected to a plain function or lambda calls it in the
    thread that emits, i.e. the worker thread, where widgets must not be
    touched. Connected to this object's method instead, the call is queued
    to the GUI thread.
    """

    def __init__(self, callback):
        """Wrap a callback.

        Args:
            callback: Function to call with the signal arguments.
        """
        super().__init__()
        self._callback = callback

    def call(self, *args):
        """Call the wrapped callback with the signal arguments."""
        self._callback(*args)


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
        # Keeps the GUI-thread callbacks of each running thread alive.
        self._callbacks: dict[QThread, list[_GuiCallback]] = {}

    def stop(self, cancel=False):
        """Stop the current worker and thread.

        Args:
            cancel: Also abort the worker if it supports it (cancel()), so
                the wait is short; it then emits nothing.
        """
        try:
            if self._thread and self._thread.isRunning():
                if cancel and hasattr(self._current_worker, "cancel"):
                    self._current_worker.cancel()
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

    def run(
        self, worker, on_finished, on_error, on_progress=None, cancel_previous=False
    ):
        """Run a worker in a background thread.

        Args:
            worker: Worker object with run(), finished, and error signals.
            on_finished: Callback for finished signal.
            on_error: Callback for error signal. If None, a generic error
                dialog is shown instead.
            on_progress: Optional callback for progress signal.
            cancel_previous: Abort the previous task instead of waiting for
                it to end (a search replaced by a newer one).

        Returns:
            The worker object.
        """
        self.stop(cancel=cancel_previous)

        self._current_worker = worker
        self._thread = QThread(self._parent)
        worker.moveToThread(self._thread)

        callbacks = self._callbacks.setdefault(self._thread, [])

        def in_gui(callback):
            """Return a slot that runs callback in the GUI thread."""
            relay = _GuiCallback(callback)
            callbacks.append(relay)
            return relay.call

        if hasattr(self._thread, "started") and hasattr(worker, "run"):
            self._thread.started.connect(worker.run)
        if hasattr(worker, "finished"):
            worker.finished.connect(in_gui(on_finished))
            worker.finished.connect(self._thread.quit)
        if hasattr(worker, "error"):

            def _handle_error(err):
                """Handle worker error signal.

                The generic dialog is only a fallback: a caller-provided
                on_error is responsible for informing the user.

                Args:
                    err: Error message from worker.
                """
                if on_error:
                    on_error(err)
                else:
                    self._show_error(err)

            worker.error.connect(in_gui(_handle_error))
            worker.error.connect(self._thread.quit)
        if on_progress and hasattr(worker, "progress"):
            worker.progress.connect(in_gui(on_progress))

        thread_ref = self._thread
        worker_ref = worker

        def _clear_if_current():
            """Clear refs only if they still point to this finished thread/worker."""
            if self._thread is thread_ref:
                self._thread = None
            if self._current_worker is worker_ref:
                self._current_worker = None
            self._callbacks.pop(thread_ref, None)

        self._thread.finished.connect(worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(_clear_if_current)

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

        message_box.critical(
            parent,
            tr("task_failed", "Task failed"),
            message,
        )
