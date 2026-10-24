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
"""GET /api/events: the events of the server as server-sent events.

The stream starts with the state of the analysis ("scan" event), then sends
each event as it happens, and a comment every 15 seconds so that proxies
keep the connection open.
"""

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from sok.server.api.auth import require_login

router = APIRouter(prefix="/api", dependencies=[Depends(require_login)])

KEEP_ALIVE_SECONDS = 15


def _message(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    bus = request.app.state.events
    first = {"type": "scan", **request.app.state.scans.summary()}

    async def stream() -> AsyncIterator[str]:
        queue = bus.subscribe()
        try:
            yield _message(first)
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), KEEP_ALIVE_SECONDS)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield _message(event)
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
