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
import asyncio
import time
from unittest.mock import MagicMock

from PySide6.QtCore import Signal

from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.workers import BaseWorker


class SlowTask(BaseWorker):
    """A task whose request takes seconds, like a search on a slow network.

    cancel() aborts it at once, and it then emits nothing.
    """

    finished = Signal(object)

    def __init__(self, name, delay):
        super().__init__(config=MagicMock())
        self.name = name
        self.delay = delay
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        loop = self._loop
        if loop and not loop.is_closed():
            loop.call_soon_threadsafe(
                lambda: [t.cancel() for t in asyncio.all_tasks(loop)]
            )

    def execute(self):
        if not self._loop or self._cancelled:
            return
        try:
            self._loop.run_until_complete(asyncio.sleep(self.delay))
        except asyncio.CancelledError:
            return
        if not self._cancelled:
            self.finished.emit([self.name])


def test_cancel_previous_aborts_the_running_task(qtbot):
    """A newer task does not wait for the one it replaces."""
    calls = []
    runner = WorkerRunner()
    runner.run(SlowTask("old", 5), calls.append, calls.append)
    qtbot.wait(100)

    start = time.perf_counter()
    runner.run(SlowTask("new", 0), calls.append, calls.append, cancel_previous=True)
    assert time.perf_counter() - start < 0.5

    qtbot.waitUntil(lambda: calls == [["new"]])
    qtbot.wait(50)
    assert calls == [["new"]]


def test_other_tasks_still_wait_for_the_previous_one(qtbot):
    """Without cancel_previous, the previous task still ends and delivers."""
    calls = []
    runner = WorkerRunner()
    runner.run(SlowTask("first", 0.2), calls.append, calls.append)
    qtbot.wait(50)
    runner.run(SlowTask("second", 0), calls.append, calls.append)

    qtbot.waitUntil(lambda: len(calls) == 2)
    assert calls == [["first"], ["second"]]
