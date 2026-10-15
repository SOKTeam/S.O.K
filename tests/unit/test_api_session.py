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

from sok.apis.music.deezer_api import DeezerApi


async def _session_and_close(api, close=False):
    session = await api._ensure_session()
    same = session is await api._ensure_session()
    if close:
        await session.close()
    return session, same


def test_session_is_reused_within_one_event_loop():
    api = DeezerApi()
    _, same = asyncio.run(_session_and_close(api, close=True))
    assert same


def test_new_event_loop_gets_a_new_session():
    """Each search worker runs its own loop; the old session is unusable."""
    api = DeezerApi()
    first, _ = asyncio.run(_session_and_close(api))
    second, _ = asyncio.run(_session_and_close(api, close=True))
    assert second is not first
