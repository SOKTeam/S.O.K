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
"""The account of S.O.K Server and its sessions.

One account, created on the first visit or from SOK_USERNAME and
SOK_PASSWORD. The password is hashed with Argon2. A login opens a session
of 30 days, kept in a cookie; the database only holds the SHA-256 of its
token. After 5 failed logins, the next attempts wait 30 seconds.
"""

import hashlib
import logging
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from sok.server.db import Database

logger = logging.getLogger(__name__)

COOKIE_NAME = "sok_session"
SESSION_DAYS = 30
MAX_FAILURES = 5
WAIT_SECONDS = 30
MIN_PASSWORD_LENGTH = 8


def auth_disabled() -> bool:
    """Whether SOK_AUTH=none turns the login off (behind a reverse proxy)."""
    return os.environ.get("SOK_AUTH", "").strip().lower() == "none"


class AccountExists(Exception):
    """The account is already created."""


class InvalidAccount(ValueError):
    """An empty user name, or a password shorter than MIN_PASSWORD_LENGTH."""


class TooManyAttempts(Exception):
    """Too many failed logins: wait retry_after seconds."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(retry_after)
        self.retry_after = retry_after


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


class Accounts:
    """The account, its login and its sessions, in the database."""

    def __init__(self, db: Database, clock: Callable[[], float] = time.time) -> None:
        self._db = db
        self._clock = clock
        self._hasher = PasswordHasher()
        self._lock = threading.Lock()
        # Times of the failed logins since the last success.
        self._failures: List[float] = []

    def _now(self) -> datetime:
        return datetime.fromtimestamp(self._clock(), timezone.utc)

    def username(self) -> Optional[str]:
        """The user name of the account, or None before it is created."""
        with self._db.transaction() as db:
            row = db.execute("SELECT username FROM account WHERE id = 1").fetchone()
        return row["username"] if row else None

    def exists(self) -> bool:
        return self.username() is not None

    def create(self, username: str, password: str) -> None:
        """Create the account.

        Raises:
            InvalidAccount: An empty user name or a too short password.
            AccountExists: The account is already created.
        """
        username = username.strip()
        if not username or len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidAccount(username)
        password_hash = self._hasher.hash(password)
        with self._db.transaction() as db:
            if db.execute("SELECT 1 FROM account").fetchone():
                raise AccountExists(username)
            db.execute(
                "INSERT INTO account (id, username, password_hash, created) "
                "VALUES (1, ?, ?, ?)",
                (username, password_hash, _iso(self._now())),
            )
        logger.info("Account %s created", username)

    def create_from_env(self) -> bool:
        """Create the account from SOK_USERNAME and SOK_PASSWORD, if none exists.

        Returns:
            True when the account was created.
        """
        username = os.environ.get("SOK_USERNAME", "")
        password = os.environ.get("SOK_PASSWORD", "")
        if not username or not password or self.exists():
            return False
        try:
            self.create(username, password)
        except InvalidAccount:
            logger.warning(
                "SOK_USERNAME/SOK_PASSWORD ignored: the password needs %d characters",
                MIN_PASSWORD_LENGTH,
            )
            return False
        except AccountExists:
            return False
        return True

    def reset_from_env(self) -> bool:
        """Give the account the password of SOK_PASSWORD, with
        SOK_RESET_PASSWORD=1: the way back from a forgotten password.

        SOK_USERNAME, when set, renames the account too. The open sessions
        are closed. Nothing else changes: the settings, the history and the
        analyses stay.

        Returns:
            True when the password was changed.
        """
        if os.environ.get("SOK_RESET_PASSWORD", "").strip().lower() not in (
            "1",
            "true",
            "yes",
            "on",
        ):
            return False
        password = os.environ.get("SOK_PASSWORD", "")
        username = os.environ.get("SOK_USERNAME", "").strip() or self.username()
        if not self.exists():
            return False
        if not username or len(password) < MIN_PASSWORD_LENGTH:
            logger.warning(
                "SOK_RESET_PASSWORD ignored: SOK_PASSWORD needs %d characters",
                MIN_PASSWORD_LENGTH,
            )
            return False
        password_hash = self._hasher.hash(password)
        with self._db.transaction() as db:
            db.execute(
                "UPDATE account SET username = ?, password_hash = ? WHERE id = 1",
                (username, password_hash),
            )
            db.execute("DELETE FROM sessions")
        with self._lock:
            self._failures.clear()
        logger.warning(
            "Password of %s reset from SOK_PASSWORD: remove SOK_RESET_PASSWORD",
            username,
        )
        return True

    def check(self, username: str, password: str) -> bool:
        """Check a login.

        Raises:
            TooManyAttempts: After MAX_FAILURES failures, until WAIT_SECONDS
                have passed since the last one.
        """
        with self._lock:
            now = self._clock()
            if len(self._failures) >= MAX_FAILURES:
                wait = self._failures[-1] + WAIT_SECONDS - now
                if wait > 0:
                    raise TooManyAttempts(int(wait) + 1)

        with self._db.transaction() as db:
            row = db.execute(
                "SELECT username, password_hash FROM account WHERE id = 1"
            ).fetchone()
        valid = False
        if row is not None:
            try:
                valid = self._hasher.verify(row["password_hash"], password)
            except (VerificationError, InvalidHashError):
                valid = False
            valid = valid and secrets.compare_digest(
                row["username"].encode(), username.strip().encode()
            )

        with self._lock:
            if valid:
                self._failures.clear()
            else:
                self._failures.append(self._clock())
        if valid and self._hasher.check_needs_rehash(row["password_hash"]):
            with self._db.transaction() as db:
                db.execute(
                    "UPDATE account SET password_hash = ? WHERE id = 1",
                    (self._hasher.hash(password),),
                )
        return valid

    def open_session(self) -> str:
        """Open a session of SESSION_DAYS days and return its token."""
        token = secrets.token_urlsafe(32)
        now = self._now()
        with self._db.transaction() as db:
            db.execute("DELETE FROM sessions WHERE expires <= ?", (_iso(now),))
            db.execute(
                "INSERT INTO sessions (token_hash, created, expires) VALUES (?, ?, ?)",
                (
                    _token_hash(token),
                    _iso(now),
                    _iso(now + timedelta(days=SESSION_DAYS)),
                ),
            )
        return token

    def session_valid(self, token: Optional[str]) -> bool:
        """Whether a token is the one of an open, unexpired session."""
        if not token:
            return False
        with self._db.transaction() as db:
            row = db.execute(
                "SELECT expires FROM sessions WHERE token_hash = ?",
                (_token_hash(token),),
            ).fetchone()
        return row is not None and row["expires"] > _iso(self._now())

    def close_session(self, token: Optional[str]) -> None:
        if not token:
            return
        with self._db.transaction() as db:
            db.execute(
                "DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),)
            )
