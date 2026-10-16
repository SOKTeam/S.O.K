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
import threading

from PySide6.QtCore import QObject, Signal

from sok.ui.controllers.worker_runner import WorkerRunner


class FakeWorker(QObject):
    finished = Signal(bool, str)
    error = Signal(str)
    progress = Signal(int, str)

    def __init__(self, fail=False):
        super().__init__()
        self.fail = fail

    def run(self):
        self.progress.emit(50, "file")
        if self.fail:
            self.error.emit("boom")
        else:
            self.finished.emit(True, "1.2.0")


def in_main_thread():
    return threading.current_thread() is threading.main_thread()


def test_callbacks_run_in_the_gui_thread(qtbot):
    """Plain functions get the results in the GUI thread (update dialog)."""
    calls = []
    runner = WorkerRunner()
    runner.run(
        FakeWorker(),
        lambda found, version: calls.append(("done", version, in_main_thread())),
        lambda err: calls.append(("error", err, in_main_thread())),
        lambda percent, name: calls.append(("progress", percent, in_main_thread())),
    )

    qtbot.waitUntil(lambda: len(calls) == 2)
    assert calls == [("progress", 50, True), ("done", "1.2.0", True)]


def test_error_callback_runs_in_the_gui_thread(qtbot):
    calls = []
    runner = WorkerRunner()
    runner.run(
        FakeWorker(fail=True),
        lambda *_: calls.append("done"),
        lambda err: calls.append((err, in_main_thread())),
    )

    qtbot.waitUntil(lambda: len(calls) == 1)
    assert calls == [("boom", True)]
