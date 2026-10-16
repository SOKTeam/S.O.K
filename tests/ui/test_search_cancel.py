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

from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.workers import SearchWorker


class SlowSearch(SearchWorker):
    """A search whose request takes seconds, like on a slow network."""

    def __init__(self, name, delay):
        super().__init__(name, "movie", config=MagicMock())
        self.delay = delay

    async def _search(self):
        await asyncio.sleep(self.delay)
        return [self._query]


def test_new_search_cancels_the_previous_one(qtbot):
    """Typing a new query used to freeze the UI until the previous request
    ended; it is now cancelled at once and reports nothing."""
    calls = []
    runner = WorkerRunner()
    runner.run(SlowSearch("old", 5), calls.append, calls.append)
    qtbot.wait(100)

    start = time.perf_counter()
    runner.run(SlowSearch("new", 0), calls.append, calls.append, cancel_previous=True)
    assert time.perf_counter() - start < 0.5

    qtbot.waitUntil(lambda: calls == [["new"]])
    qtbot.wait(50)
    assert calls == [["new"]]


def test_other_tasks_still_wait_for_the_previous_one(qtbot):
    """Without cancel_previous (e.g. a row rescan), the previous search
    still ends and delivers its results."""
    calls = []
    runner = WorkerRunner()
    runner.run(SlowSearch("first", 0.2), calls.append, calls.append)
    qtbot.wait(50)
    runner.run(SlowSearch("second", 0), calls.append, calls.append)

    qtbot.waitUntil(lambda: len(calls) == 2)
    assert calls == [["first"], ["second"]]
