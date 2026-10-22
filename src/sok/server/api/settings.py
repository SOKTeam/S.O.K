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
"""The settings: /api/settings, /api/settings/test-link and test-key.

An error gives {"code", "item"} in "detail": unknown_setting,
invalid_value, unknown_key, key_locked, unknown_folder_role or
invalid_folder, and what it is about.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from sok.apis.key_check import check_key
from sok.config.api_registry import get_service
from sok.core.history import LINK
from sok.core.media_manager import reset_media_manager
from sok.server.api.auth import require_login
from sok.server.settings import (
    PREFERRED_API_SETTINGS,
    InvalidSetting,
    Settings,
    as_dict,
    check_link,
)

router = APIRouter(prefix="/api/settings", dependencies=[Depends(require_login)])


class SettingsChange(BaseModel):
    settings: Optional[Dict[str, Any]] = None
    keys: Optional[Dict[str, str]] = None
    folders: Optional[Dict[str, List[str]]] = None


class LinkTest(BaseModel):
    source: str
    destination: str


class KeyTest(BaseModel):
    service: str
    # The key typed, not saved yet; without it, the saved one.
    key: Optional[str] = None
    secret: Optional[str] = None


def settings(request: Request) -> Settings:
    return request.app.state.settings


def _read(request: Request) -> dict:
    current = settings(request)
    values = current.values()
    return {
        "settings": values,
        "languages": request.app.state.config.get_available_languages(),
        # The choices of the preferred_api_* settings.
        "services": current.services(),
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
    if change.keys or PREFERRED_API_SETTINGS.keys() & (change.settings or {}).keys():
        # The next search builds its API clients with the new keys and
        # services.
        reset_media_manager()
    return _read(request)


@router.post("/test-link")
def test_link(test: LinkTest) -> dict:
    """Whether a hard link works from a folder to another."""
    return as_dict(check_link(test.source, test.destination))


@router.post("/test-key")
async def test_key(test: KeyTest, request: Request) -> dict:
    """Whether the key of a service works: ok, wrong_key, missing_key,
    rate_limited, service_error, unreachable or unsupported. The key is
    never sent back."""
    config = request.app.state.config
    service = get_service(test.service)
    key, secret = test.key, test.secret
    if service is not None:
        if key is None and service.config_key:
            key = config.get(service.config_key, "")
        if secret is None and service.secret_config_key:
            secret = config.get(service.secret_config_key, "")
    check = await check_key(test.service, (key or "").strip(), (secret or "").strip())
    return {"service": check.service, "status": check.status, "detail": check.detail}
