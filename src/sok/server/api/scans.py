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
"""The analyses: /api/scans, /api/scans/current and /api/to-check.

An error gives a code in "detail": already_running, no_sources,
unknown_file or invalid_kind.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from sok.core.interfaces import ContentType
from sok.server.api.auth import require_login
from sok.server.scans import MEDIA_TYPE_OF, ScanError, Scans, UnknownFile

router = APIRouter(prefix="/api", dependencies=[Depends(require_login)])


class TypeChoice(BaseModel):
    path: str
    # movie, episode, album, track, book or game.
    kind: str


def scans(request: Request) -> Scans:
    return request.app.state.scans


@router.post("/scans", status_code=status.HTTP_202_ACCEPTED)
async def start_scan(request: Request) -> dict:
    """Start an analysis of the source folders; it runs in the background."""
    try:
        scan_id = scans(request).start()
    except ScanError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, exc.code)
    return {"id": scan_id}


@router.get("/scans/current")
def current_scan(request: Request) -> dict:
    """The last analysis, the counts of the rows, the files to check."""
    return scans(request).summary()


@router.post("/to-check")
def confirm_type(choice: TypeChoice, request: Request) -> dict:
    """Give a file to check its type; answers with the new summary."""
    try:
        kind = ContentType(choice.kind)
    except ValueError:
        kind = None
    if kind not in MEDIA_TYPE_OF:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_kind")
    try:
        scans(request).confirm(choice.path, kind)
    except UnknownFile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_file")
    return scans(request).summary()
