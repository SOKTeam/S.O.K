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
"""The settings of S.O.K Server.

The settings shared with the desktop app (formats, file mode, behavior,
language, API keys) stay in config.json through the ConfigManager, where
the core reads them. The folders, which only the server has, are in the
database. A key never leaves the server: the settings only say whether it
is set, and whether an environment variable locks it.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from sok.config.api_registry import get_all_services, get_services_by_media_type
from sok.config.config_manager import ConfigManager
from sok.core.history import FILE_MODES
from sok.core.utils import natural_key
from sok.file_operations.base_operations import can_hard_link
from sok.server.db import Database

# The settings the server shows and changes, with their type.
BOOL_SETTINGS = (
    "create_folders",
    "skip_duplicates",
    "backup_before_rename",
    "subtitles_follow_video",
    "download_posters",
)
FORMAT_SETTINGS = (
    "movie_format",
    "video_format",
    "music_format",
    "book_format",
    "game_format",
)
# The service searched for each media type of the registry.
PREFERRED_API_SETTINGS = {
    "preferred_api_video": "video",
    "preferred_api_music": "music",
    "preferred_api_books": "books",
    "preferred_api_games": "games",
}
SETTINGS = (
    ("language", "file_mode")
    + BOOL_SETTINGS
    + FORMAT_SETTINGS
    + tuple(PREFERRED_API_SETTINGS)
)

# The tabs of the interface, each with its destination folders.
MEDIA_TYPES = ("movies", "tv", "music", "books", "games")
SOURCES = "sources"

# Why a hard link fails between two folders (LinkCheck.problem).
DIFFERENT_DRIVES = "different_drives"
NO_HARD_LINKS = "no_hard_links"
MISSING_FOLDER = "missing_folder"

# Files looked at to find one to link, in a source with many folders.
MAX_SCANNED = 1000

# Folders listed at most by the folder browser, in one folder.
MAX_LISTED = 1000


class InvalidSetting(ValueError):
    """A setting, key or folder that cannot be saved: code and what it is."""

    def __init__(self, code: str, item: str) -> None:
        super().__init__(f"{code}: {item}")
        self.code = code
        self.item = item


@dataclass
class LinkCheck:
    """Whether a hard link works from a source to a destination."""

    source: str
    destination: str
    problem: Optional[str] = None
    # False when the source holds no file to link: only the drives were
    # compared.
    tested: bool = True

    @property
    def ok(self) -> bool:
        return self.problem is None


def _first_file(folder: str) -> Optional[str]:
    """A file of the folder or of its subfolders, if there is one."""
    seen = 0
    for root, _dirs, files in os.walk(folder):
        for name in files:
            return os.path.join(root, name)
        seen += 1
        if seen >= MAX_SCANNED:
            break
    return None


def check_link(source: str, destination: str) -> LinkCheck:
    """Check that a hard link works from a source folder to a destination.

    The two folders must be on the same device, which two Docker mounts are
    not, even on one disk; then a test link of a file of the source must
    work (FAT, exFAT and most network shares have no hard links).
    """
    check = LinkCheck(source, destination)
    try:
        same_device = os.stat(source).st_dev == os.stat(destination).st_dev
    except OSError:
        check.problem = MISSING_FOLDER
        return check
    if not same_device:
        check.problem = DIFFERENT_DRIVES
        return check
    file = _first_file(source)
    if file is None:
        check.tested = False
    elif not can_hard_link(file, destination):
        check.problem = NO_HARD_LINKS
    return check


class Settings:
    """Read and change the settings of the server."""

    def __init__(self, db: Database, config: ConfigManager) -> None:
        self._db = db
        self._config = config

    # ------------------------------------------------------------ Folders

    def folders(self) -> Dict[str, List[str]]:
        """The source folders, and the destination folders of each type."""
        result: Dict[str, List[str]] = {role: [] for role in (SOURCES,) + MEDIA_TYPES}
        with self._db.transaction() as db:
            rows = db.execute(
                "SELECT role, path FROM folders ORDER BY role, position"
            ).fetchall()
        for row in rows:
            if row["role"] in result:
                result[row["role"]].append(row["path"])
        return result

    def _clean_folders(self, folders: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """The folders of the roles given, checked and without duplicates.

        Raises:
            InvalidSetting: An unknown role, or a path that is not an
                existing folder (an absolute path, as seen by the server).
        """
        cleaned: Dict[str, List[str]] = {}
        for role, paths in folders.items():
            if role not in (SOURCES,) + MEDIA_TYPES:
                raise InvalidSetting("unknown_folder_role", role)
            kept: List[str] = []
            for path in paths:
                path = path.strip()
                if not os.path.isabs(path) or not os.path.isdir(path):
                    raise InvalidSetting("invalid_folder", path)
                path = os.path.normpath(path)
                if path not in kept:
                    kept.append(path)
            cleaned[role] = kept
        return cleaned

    def _write_folders(self, folders: Dict[str, List[str]]) -> None:
        with self._db.transaction() as db:
            for role, paths in folders.items():
                db.execute("DELETE FROM folders WHERE role = ?", (role,))
                db.executemany(
                    "INSERT INTO folders (role, position, path) VALUES (?, ?, ?)",
                    [(role, i, path) for i, path in enumerate(paths)],
                )

    def link_checks(self) -> List[LinkCheck]:
        """A check of every source with every destination folder."""
        folders = self.folders()
        destinations = []
        for media_type in MEDIA_TYPES:
            for path in folders[media_type]:
                if path not in destinations:
                    destinations.append(path)
        return [
            check_link(source, destination)
            for source in folders[SOURCES]
            for destination in destinations
        ]

    # ---------------------------------------------------------- Settings

    def values(self) -> Dict[str, Any]:
        return {key: self._config.get(key) for key in SETTINGS}

    def _check_values(self, values: Dict[str, Any]) -> None:
        """Raises InvalidSetting for an unknown setting or a wrong value."""
        languages = self._config.get_available_languages()
        for key, value in values.items():
            if key not in SETTINGS:
                raise InvalidSetting("unknown_setting", key)
            valid = (
                (key in BOOL_SETTINGS and isinstance(value, bool))
                or (key in FORMAT_SETTINGS and isinstance(value, str) and value.strip())
                or (key == "file_mode" and value in FILE_MODES)
                or (key == "language" and value in languages)
                or (
                    key in PREFERRED_API_SETTINGS
                    and value
                    in [
                        s.id
                        for s in get_services_by_media_type(PREFERRED_API_SETTINGS[key])
                    ]
                )
            )
            if not valid:
                raise InvalidSetting("invalid_value", key)

    # --------------------------------------------------------------- Keys

    def _key_fields(self) -> Iterator[tuple]:
        """(service, config key) of every key a service takes."""
        fields = vars(self._config.config)
        for service in get_all_services():
            keys = [service.config_key]
            if service.requires_secret:
                keys.append(service.secret_config_key)
            for key in keys:
                # Only the keys the settings can save.
                if key and key in fields:
                    yield service, key

    @staticmethod
    def services() -> Dict[str, List[Dict[str, str]]]:
        """The services a preferred_api_* setting can pick, per media type."""
        return {
            media_type: [
                {"id": s.id, "name": s.name}
                for s in get_services_by_media_type(media_type)
            ]
            for media_type in PREFERRED_API_SETTINGS.values()
        }

    def keys(self) -> List[Dict[str, Any]]:
        """The services and their keys: set or not, locked or not; no value."""
        services: Dict[str, Dict[str, Any]] = {}
        for service, key in self._key_fields():
            entry = services.setdefault(
                service.id,
                {
                    "service": service.id,
                    "name": service.name,
                    "media_type": service.media_type,
                    "url": service.api_key_url,
                    "keys": [],
                },
            )
            entry["keys"].append(
                {
                    "key": key,
                    "set": bool(self._config.get_user_value(key))
                    or self._config.from_env(key),
                    "locked": self._config.env_locked(key),
                }
            )
        return list(services.values())

    def _check_keys(self, keys: Dict[str, str]) -> None:
        """Raises InvalidSetting for an unknown key, or one an environment
        variable locks."""
        known = {key for _service, key in self._key_fields()}
        for key in keys:
            if key not in known:
                raise InvalidSetting("unknown_key", key)
            if self._config.env_locked(key):
                raise InvalidSetting("key_locked", key)

    # ------------------------------------------------------------- Update

    def update(
        self,
        values: Optional[Dict[str, Any]] = None,
        keys: Optional[Dict[str, str]] = None,
        folders: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """Change settings, keys (an empty value removes one) and folders.

        Everything is checked first: all of it is saved, or nothing.

        Raises:
            InvalidSetting: The first thing that cannot be saved.
        """
        values, keys = values or {}, keys or {}
        self._check_values(values)
        self._check_keys(keys)
        cleaned = self._clean_folders(folders or {})
        for key, value in values.items():
            self._config.set(key, value.strip() if isinstance(value, str) else value)
        for key, value in keys.items():
            self._config.set(key, value.strip())
        self._write_folders(cleaned)


class UnreadableFolder(OSError):
    """A folder that is missing, or that the server cannot read."""


def browse(path: Optional[str] = None) -> Dict[str, Any]:
    """The subfolders of a folder of the server, for the folder browser of
    the settings: the browser cannot see the disks of the server.

    Args:
        path: An absolute path; the root of the file system when empty.

    Returns:
        {"path", "parent" (None at the root), "folders": [{"name", "path"}]},
        hidden folders left out, sorted by name, at most MAX_LISTED.

    Raises:
        UnreadableFolder: The path is not an absolute folder, or cannot be
            read.
    """
    folder = Path(path) if path else Path(Path.cwd().anchor)
    if not folder.is_absolute() or not folder.is_dir():
        raise UnreadableFolder(str(folder))
    folder = Path(os.path.normpath(folder))
    folders: List[Dict[str, str]] = []
    try:
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                try:
                    if entry.is_dir():
                        folders.append({"name": entry.name, "path": entry.path})
                except OSError:
                    continue
    except OSError as exc:
        raise UnreadableFolder(str(folder)) from exc
    folders.sort(key=lambda f: natural_key(Path(f["name"])))
    parent = folder.parent
    return {
        "path": str(folder),
        "parent": None if parent == folder else str(parent),
        "folders": folders[:MAX_LISTED],
    }


def as_dict(check: LinkCheck) -> Dict[str, Any]:
    return {
        "source": check.source,
        "destination": check.destination,
        "ok": check.ok,
        "problem": check.problem,
        "tested": check.tested,
    }
