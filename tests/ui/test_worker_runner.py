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
from unittest.mock import MagicMock

from PySide6.QtCore import QObject, Signal

from sok.ui.controllers.worker_runner import WorkerRunner


class FailingWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def run(self):
        self.error.emit("boom")


def run_and_fail(qtbot, on_error):
    runner = WorkerRunner()
    runner._show_error = MagicMock()
    runner.run(FailingWorker(), lambda _: None, on_error)
    qtbot.waitUntil(lambda: runner._show_error.called or (on_error and on_error.called))
    runner.stop()
    return runner


class TestWorkerRunnerErrors:
    def test_caller_error_handler_replaces_generic_dialog(self, qtbot):
        on_error = MagicMock()

        runner = run_and_fail(qtbot, on_error)

        on_error.assert_called_once_with("boom")
        runner._show_error.assert_not_called()

    def test_generic_dialog_without_error_handler(self, qtbot):
        runner = run_and_fail(qtbot, None)

        runner._show_error.assert_called_once_with("boom")
