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
"""The renames and the history: /api/renames, /api/renames/current,
/api/history, /api/history/{id}/undo, and the files already processed:
/api/processed and /api/processed/forget.

An error gives a code in "detail": unknown_type, nothing_to_rename,
no_destination, scan_running, already_running, unknown_operation; a hard link
that cannot be made gives {"code": "different_drives", "no_hard_links" or
"missing_folder", "source", "destination"}.
"""

import asyncio
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from sok.server.api.auth import require_login
from sok.server.history import (
    History,
    UnknownOperation,
    describe,
    forget_processed,
    processed_files,
    undo_report,
)
from sok.server.jobs import RENAME, Busy
from sok.server.renames import Renamer, RenameError

router = APIRouter(prefix="/api", dependencies=[Depends(require_login)])


class RenameRequest(BaseModel):
    # The tab: movies, tv, music, books or games.
    type: str
    # Only these rows; all the Ready rows of the tab when absent.
    rows: Optional[List[int]] = None


class UndoRequest(BaseModel):
    # One file of the operation (its index); the whole operation when absent.
    index: Optional[int] = None


def renamer(request: Request) -> Renamer:
    return request.app.state.renamer


def history(request: Request) -> History:
    return request.app.state.history


@router.post("/renames", status_code=status.HTTP_202_ACCEPTED)
async def start_rename(rename: RenameRequest, request: Request) -> dict:
    """Rename the Ready rows of a tab; it runs in the background."""
    try:
        rename_id = renamer(request).start(rename.type, rename.rows)
    except RenameError as exc:
        code = (
            status.HTTP_422_UNPROCESSABLE_CONTENT
            if exc.code == "unknown_type"
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(code, exc.detail() if exc.details else exc.code)
    return {"id": rename_id}


@router.get("/renames/current")
def current_rename(request: Request) -> dict:
    """The last rename, its progress or its result."""
    return renamer(request).current()


@router.get("/history")
def list_history(request: Request) -> dict:
    """The operations of the history, newest first."""
    return {"operations": [describe(op) for op in history(request).operations()]}


@router.post("/history/{operation_id}/undo")
async def undo(operation_id: str, undo: UndoRequest, request: Request) -> dict:
    """Put back the files of an operation, or one of them with its
    subtitles; answers what was put back and the operation."""
    try:
        request.app.state.jobs.check(RENAME)
    except Busy as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, exc.code)
    try:
        report = await asyncio.to_thread(
            history(request).undo_checked, operation_id, undo.index
        )
    except UnknownOperation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_operation")
    operation = history(request).get(operation_id)
    assert operation is not None
    return {**undo_report(report), "operation": describe(operation)}


class ProcessedFiles(BaseModel):
    paths: List[str]


@router.get("/processed")
def list_processed(request: Request) -> dict:
    """The files already processed, which the analyses leave out."""
    return {"files": processed_files(request.app.state.db)}


@router.post("/processed/forget")
def forget(files: ProcessedFiles, request: Request) -> dict:
    """Analyze these files again, at the next analysis."""
    return {"forgotten": forget_processed(request.app.state.db, files.paths)}
