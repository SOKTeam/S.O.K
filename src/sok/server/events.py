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
"""The events of the server, sent live to the browsers (GET /api/events).

Each browser tab that listens gets a queue; publish() puts an event in all
of them. An event is a dict with a "type", such as {"type": "scan", ...}.
"""

import asyncio
from typing import Any, Dict, List

# Events kept for a listener that reads too slowly; older ones are dropped.
QUEUE_SIZE = 100


class EventBus:
    """Hands every published event to every listener."""

    def __init__(self) -> None:
        self._queues: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(QUEUE_SIZE)
        self._queues.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        if queue in self._queues:
            self._queues.remove(queue)

    @property
    def listeners(self) -> int:
        return len(self._queues)

    def publish(self, event: Dict[str, Any]) -> None:
        """Send an event; called from the event loop of the server."""
        for queue in self._queues:
            if queue.full():
                # A progress event replaces the oldest one: the newest says
                # more.
                queue.get_nowait()
            queue.put_nowait(event)
