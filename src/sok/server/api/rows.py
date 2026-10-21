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
"""The rows of the tabs: /api/rows, /api/rows/{id}, /api/rows/{id}/search.

An error gives a code in "detail": unknown_type, unknown_row,
invalid_selection, invalid_destination, not_searched, or the code of a
stopped search ({"code": "missing_key", "service": "tmdb"}).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from sok.server.api.auth import require_login
from sok.server.search import (
    InvalidChange,
    Searcher,
    SearchStopped,
    UnknownRow,
    search_error,
)
from sok.server.settings import MEDIA_TYPES

router = APIRouter(prefix="/api/rows", dependencies=[Depends(require_login)])


class RowChange(BaseModel):
    # Index of the candidate picked: the row is then Ready.
    selected: Optional[int] = None
    # Index of the destination folder of its media type.
    destination: Optional[int] = None


class RowSearch(BaseModel):
    # The text to search instead of the one read from the file names.
    query: Optional[str] = None


def searcher(request: Request) -> Searcher:
    return request.app.state.searcher


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "unknown_row")


@router.get("")
def list_rows(type: str, request: Request) -> dict:
    """The rows of a tab: movies, tv, music, books or games."""
    if type not in MEDIA_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "unknown_type")
    return {"rows": searcher(request).rows(type)}


@router.get("/{row_id}")
def read_row(row_id: int, request: Request) -> dict:
    try:
        return searcher(request).row(row_id)
    except UnknownRow:
        raise _not_found()


@router.patch("/{row_id}")
async def change_row(row_id: int, change: RowChange, request: Request) -> dict:
    """Pick a candidate or a destination; answers the row."""
    try:
        media_type = searcher(request).row(row_id)["media_type"]
        destinations = len(request.app.state.settings.folders()[media_type])
        await searcher(request).change(
            row_id, change.selected, change.destination, destinations
        )
    except UnknownRow:
        raise _not_found()
    except InvalidChange as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.code)
    return searcher(request).row(row_id)


@router.post("/{row_id}/search")
async def search_row(row_id: int, search: RowSearch, request: Request) -> dict:
    """Search a row again, with the text typed; answers the row."""
    try:
        await searcher(request).search_row(row_id, search.query)
    except UnknownRow:
        raise _not_found()
    except InvalidChange as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.code)
    except SearchStopped as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, search_error(exc))
    return searcher(request).row(row_id)
