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
"""The background work of S.O.K Server: one analysis or one rename at a time.

An analysis must not sort files that a rename is moving, and a rename must
not move files an analysis is sorting: they share one slot.
"""

import asyncio
from typing import Any, Coroutine, Optional

# What runs in the slot (Jobs.kind).
SCAN = "scan"
RENAME = "rename"


class Busy(Exception):
    """The slot is taken: already_running for a job of the same kind, else
    scan_running or rename_running."""

    def __init__(self, running: str, wanted: str) -> None:
        self.code = "already_running" if running == wanted else f"{running}_running"
        super().__init__(self.code)


class Jobs:
    """The slot of the background work."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self.kind: Optional[str] = None

    def running(self, kind: Optional[str] = None) -> bool:
        """Whether a job runs; of this kind only, when given."""
        busy = self._task is not None and not self._task.done()
        return busy and (kind is None or self.kind == kind)

    def check(self, kind: str) -> None:
        """Raise Busy when the slot is taken."""
        if self.running():
            assert self.kind is not None
            raise Busy(self.kind, kind)

    def start(self, kind: str, work: Coroutine[Any, Any, None]) -> None:
        """Run a job in the background.

        Raises:
            Busy: Another job runs; the work is not started.
        """
        try:
            self.check(kind)
        except Busy:
            work.close()
            raise
        self.kind = kind
        self._task = asyncio.get_running_loop().create_task(work)

    async def wait(self) -> None:
        """Wait for the running job, if any (for the tests)."""
        if self._task is not None:
            await asyncio.shield(self._task)
