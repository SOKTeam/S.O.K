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
"""GET /api/health: the health check of Docker, without login."""

from fastapi import APIRouter, Request

from sok.__version__ import __version__

router = APIRouter(prefix="/api")


@router.get("/health")
def health(request: Request) -> dict:
    """Answers once the database is open."""
    return {"status": "ok", "version": __version__, "db": request.app.state.db.version}
