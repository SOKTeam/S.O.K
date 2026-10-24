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
"""The automatic sorting: GET /api/watch.

The auto_sort and auto_sort_minutes settings turn it on and set its pace
(PATCH /api/settings); the events of type "watch" give the same status.
"""

from fastapi import APIRouter, Depends, Request

from sok.server.api.auth import require_login

router = APIRouter(prefix="/api", dependencies=[Depends(require_login)])


@router.get("/watch")
def watch_status(request: Request) -> dict:
    """Whether the automatic sorting is on, its last check and last run."""
    return request.app.state.watcher.status()
