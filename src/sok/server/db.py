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
"""The database of S.O.K Server: sok.db, a SQLite file next to config.json.

The schema grows by steps (MIGRATIONS); PRAGMA user_version says how many
are applied, so an older database is brought up to date when it opens.
"""

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List

# One entry per version of the schema, applied in order and never changed
# once released: a change of the schema is a new entry.
MIGRATIONS: List[str] = [
    """
    CREATE TABLE account (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        username TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created TEXT NOT NULL
    );
    CREATE TABLE sessions (
        token_hash TEXT PRIMARY KEY,
        created TEXT NOT NULL,
        expires TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE folders (
        role TEXT NOT NULL,
        position INTEGER NOT NULL,
        path TEXT NOT NULL,
        PRIMARY KEY (role, position)
    );
    """,
    """
    CREATE TABLE scans (
        id INTEGER PRIMARY KEY,
        started TEXT NOT NULL,
        finished TEXT,
        status TEXT NOT NULL,
        error TEXT,
        missing_sources TEXT NOT NULL DEFAULT '[]'
    );
    CREATE TABLE rows (
        id INTEGER PRIMARY KEY,
        key TEXT NOT NULL UNIQUE,
        media_type TEXT NOT NULL,
        kind TEXT NOT NULL,
        title TEXT,
        files TEXT NOT NULL,
        query TEXT,
        year INTEGER,
        candidates TEXT NOT NULL DEFAULT '[]',
        selected INTEGER,
        status TEXT NOT NULL,
        destination INTEGER NOT NULL DEFAULT 0,
        details TEXT
    );
    CREATE INDEX rows_media_type ON rows (media_type);
    CREATE TABLE to_check (
        path TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        title TEXT,
        reason TEXT NOT NULL
    );
    CREATE TABLE type_choices (
        path TEXT PRIMARY KEY,
        kind TEXT NOT NULL
    );
    """,
]


class Database:
    """The SQLite file, shared by the requests of the server."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        # True when this opening created the database: a new installation.
        self.created = self.version == 0
        self._migrate()

    def _migrate(self) -> None:
        with self._lock:
            version = self._connection.execute("PRAGMA user_version").fetchone()[0]
            for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
                self._connection.executescript(
                    f"BEGIN; {script} PRAGMA user_version = {number}; COMMIT;"
                )

    @property
    def version(self) -> int:
        """The number of migrations applied."""
        with self._lock:
            return self._connection.execute("PRAGMA user_version").fetchone()[0]

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run the statements of the block together: all of them, or none."""
        with self._lock:
            with self._connection:
                yield self._connection

    def close(self) -> None:
        with self._lock:
            self._connection.close()
