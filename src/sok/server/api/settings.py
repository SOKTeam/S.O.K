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
"""The settings: /api/settings and /api/settings/test-link.

An error gives {"code", "item"} in "detail": unknown_setting,
invalid_value, unknown_key, key_locked, unknown_folder_role or
invalid_folder, and what it is about.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from sok.core.history import LINK
from sok.core.media_manager import reset_media_manager
from sok.server.api.auth import require_login
from sok.server.settings import InvalidSetting, Settings, as_dict, check_link

router = APIRouter(prefix="/api/settings", dependencies=[Depends(require_login)])


class SettingsChange(BaseModel):
    settings: Optional[Dict[str, Any]] = None
    keys: Optional[Dict[str, str]] = None
    folders: Optional[Dict[str, List[str]]] = None


class LinkTest(BaseModel):
    source: str
    destination: str


def settings(request: Request) -> Settings:
    return request.app.state.settings


def _read(request: Request) -> dict:
    current = settings(request)
    values = current.values()
    return {
        "settings": values,
        "languages": request.app.state.config.get_available_languages(),
        "keys": current.keys(),
        "folders": current.folders(),
        # Only the hard link mode needs them.
        "link_checks": (
            [as_dict(check) for check in current.link_checks()]
            if values["file_mode"] == LINK
            else []
        ),
    }


@router.get("")
def read_settings(request: Request) -> dict:
    """The settings, the keys (set or not, locked or not) and the folders."""
    return _read(request)


@router.patch("")
def change_settings(change: SettingsChange, request: Request) -> dict:
    """Change some settings; answers with all of them, as GET does."""
    try:
        settings(request).update(change.settings, change.keys, change.folders)
    except InvalidSetting as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            {"code": exc.code, "item": exc.item},
        )
    if change.keys:
        # The next search builds its API clients with the new keys.
        reset_media_manager()
    return _read(request)


@router.post("/test-link")
def test_link(test: LinkTest) -> dict:
    """Whether a hard link works from a folder to another."""
    return as_dict(check_link(test.source, test.destination))
