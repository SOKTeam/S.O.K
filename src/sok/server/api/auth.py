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
"""Account and session: /api/session, /api/setup, /api/login, /api/logout.

The errors give a code in "detail" (account_exists, invalid_account,
wrong_login, too_many_attempts, not_logged_in), which the interface
translates.
"""

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from sok.server.auth import (
    COOKIE_NAME,
    SESSION_DAYS,
    AccountExists,
    Accounts,
    InvalidAccount,
    TooManyAttempts,
    auth_disabled,
)

router = APIRouter(prefix="/api")


class Credentials(BaseModel):
    username: str
    password: str


def accounts(request: Request) -> Accounts:
    return request.app.state.accounts


def logged_in(request: Request) -> bool:
    """Whether the request has an open session, or the login is turned off."""
    return auth_disabled() or accounts(request).session_valid(
        request.cookies.get(COOKIE_NAME)
    )


def require_login(request: Request) -> None:
    """Dependency of the routes that need a session."""
    if not logged_in(request):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not_logged_in")


def _set_session(request: Request, response: Response) -> None:
    response.set_cookie(
        COOKIE_NAME,
        accounts(request).open_session(),
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="strict",
        # Plain HTTP on a home network is common: Secure only over HTTPS.
        secure=request.url.scheme == "https",
    )


@router.get("/session")
def session(request: Request) -> dict:
    """What the interface shows first: the setup, the login or the app."""
    return {
        "auth": "none" if auth_disabled() else "login",
        "account": accounts(request).exists(),
        "logged_in": logged_in(request),
        "username": accounts(request).username(),
    }


@router.post("/setup", status_code=status.HTTP_201_CREATED)
def setup(credentials: Credentials, request: Request, response: Response) -> dict:
    """Create the account on the first visit, and log in."""
    try:
        accounts(request).create(credentials.username, credentials.password)
    except AccountExists:
        raise HTTPException(status.HTTP_409_CONFLICT, "account_exists")
    except InvalidAccount:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "invalid_account")
    _set_session(request, response)
    return {"username": credentials.username.strip()}


@router.post("/login")
def login(credentials: Credentials, request: Request, response: Response) -> dict:
    try:
        valid = accounts(request).check(credentials.username, credentials.password)
    except TooManyAttempts as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "too_many_attempts",
            headers={"Retry-After": str(exc.retry_after)},
        )
    if not valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong_login")
    _set_session(request, response)
    return {"username": accounts(request).username()}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response) -> None:
    accounts(request).close_session(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, httponly=True, samesite="strict")
