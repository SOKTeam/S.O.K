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
"""The notifications of S.O.K Server, after each rename that moved files.

Each target set in the settings gets the rename, by hand or automatic:

- Discord: a message to a webhook of a channel;
- Jellyfin and Plex: a refresh of their libraries;
- a webhook: the rename as JSON (RenameEvent), for Home Assistant, n8n…;
- a script: the command of SOK_AFTER_RENAME, run without a shell, with the
  JSON on its standard input and SOK_EVENT, SOK_MEDIA_TYPE, SOK_RENAMED and
  SOK_AUTO in its environment.

A target that fails is logged and does not stop the others, nor the rename.
"""

import asyncio
import json
import logging
import os
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import aiohttp

from sok.config.config_manager import ConfigManager
from sok.server.settings import SCRIPT_VARIABLE, Settings

logger = logging.getLogger(__name__)

TARGETS = ("discord", "jellyfin", "plex", "webhook", "script")

# Seconds given to a target to answer, and to the script to end.
TIMEOUT = 15
SCRIPT_TIMEOUT = 300

# The file names a Discord message lists at most.
MAX_LISTED = 10

# The names of the tabs, as the interface gives them (key, English).
TAB_NAMES = {
    "movies": ("movies", "Movies"),
    "tv": ("tv_shows", "TV Shows"),
    "music": ("music", "Music"),
    "books": ("books", "Books"),
    "games": ("games", "Games"),
}

# (method, url, headers, json) → HTTP status.
Request = Callable[[str, str, Dict[str, str], Optional[Any]], Awaitable[int]]


class NotifyError(Exception):
    """A target that did not take the notification: why, in a few words."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def http_request(
    method: str, url: str, headers: Dict[str, str], body: Optional[Any]
) -> int:
    """Send a request; returns its status."""
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.request(method, url, headers=headers, json=body) as answer:
            return answer.status


class Notifier:
    """Send a rename to every target of the settings."""

    def __init__(
        self,
        settings: Settings,
        config: ConfigManager,
        request: Request = http_request,
    ) -> None:
        self._settings = settings
        self._config = config
        self._request = request
        # The notifications on their way: a task needs a reference.
        self._tasks: set = set()

    def renamed_later(self, event: Dict[str, Any]) -> None:
        """Send a rename in the background (called by the Renamer)."""
        task = asyncio.get_running_loop().create_task(self.renamed(event))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def renamed(self, event: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Send a rename to every target set.

        Args:
            event: {"media_type", "auto", "renamed", "files": [{"from",
                "to"}]}; "event" and "date" are added.

        Returns:
            For each target set, None when it worked, else why it failed.
        """
        event = {"event": "renamed", "date": _now(), **event}
        results: Dict[str, Optional[str]] = {}
        for target in self._targets():
            results[target] = await self._send(target, event)
        return results

    async def test(self, target: str) -> Optional[str]:
        """Send a test to one target; None when it worked, else why not.

        Raises:
            ValueError: An unknown target.
        """
        if target not in TARGETS:
            raise ValueError(target)
        if target not in self._targets():
            return "not_set"
        event: Dict[str, Any] = {
            "event": "test",
            "date": _now(),
            "media_type": None,
            "auto": False,
            "renamed": 0,
            "files": [],
        }
        return await self._send(target, event)

    def _targets(self) -> List[str]:
        values = self._settings.notify_values()
        targets = []
        if "discord_url" in values:
            targets.append("discord")
        if "jellyfin_url" in values and "jellyfin_key" in values:
            targets.append("jellyfin")
        if "plex_url" in values and "plex_token" in values:
            targets.append("plex")
        if "webhook_url" in values:
            targets.append("webhook")
        if os.environ.get(SCRIPT_VARIABLE, "").strip():
            targets.append("script")
        return targets

    async def _send(self, target: str, event: Dict[str, Any]) -> Optional[str]:
        try:
            if target == "script":
                await self._run_script(event)
            else:
                await self._post(target, event)
        except Exception as exc:  # noqa: BLE001 - a target must not stop others
            reason = str(exc) or type(exc).__name__
            logger.warning("Notification to %s failed: %s", target, reason)
            return reason[:300]
        return None

    async def _post(self, target: str, event: Dict[str, Any]) -> None:
        values = self._settings.notify_values()
        call: Tuple[str, str, Dict[str, str], Optional[Any]]
        if target == "discord":
            call = (
                "POST",
                values["discord_url"],
                {},
                {"content": self._message(event)},
            )
        elif target == "jellyfin":
            call = (
                "POST",
                f"{values['jellyfin_url']}/Library/Refresh",
                {"X-Emby-Token": values["jellyfin_key"]},
                None,
            )
        elif target == "plex":
            call = (
                "GET",
                f"{values['plex_url']}/library/sections/all/refresh",
                {"X-Plex-Token": values["plex_token"]},
                None,
            )
        else:
            call = ("POST", values["webhook_url"], {}, event)
        status = await self._request(*call)
        if status >= 400:
            raise NotifyError(f"HTTP {status}")

    async def _run_script(self, event: Dict[str, Any]) -> None:
        command = shlex.split(os.environ.get(SCRIPT_VARIABLE, ""))
        environment = {
            **os.environ,
            "SOK_EVENT": event["event"],
            "SOK_MEDIA_TYPE": event["media_type"] or "",
            "SOK_RENAMED": str(event["renamed"]),
            "SOK_AUTO": "1" if event["auto"] else "0",
        }
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            env=environment,
        )
        try:
            _, errors = await asyncio.wait_for(
                process.communicate(json.dumps(event).encode()), SCRIPT_TIMEOUT
            )
        except asyncio.TimeoutError:
            process.kill()
            raise NotifyError(f"no end after {SCRIPT_TIMEOUT} s")
        if process.returncode:
            detail = errors.decode(errors="replace").strip().splitlines()
            raise NotifyError(
                f"exit code {process.returncode}"
                + (f": {detail[-1]}" if detail else "")
            )

    def _message(self, event: Dict[str, Any]) -> str:
        """The Discord message, in the language of the settings."""
        texts = self._config.load_language()

        def t(key: str, english: str, **values: Any) -> str:
            return (texts.get(key) or english).format(**values)

        if event["event"] == "test":
            return t("notify_test", "S.O.K Server: the notifications work.")
        key, english = TAB_NAMES.get(event["media_type"], ("", event["media_type"]))
        lines = [
            f"**S.O.K Server** · {t(key, english) if key else english}",
            t(
                "notify_auto_renamed",
                "Files sorted automatically: {n}",
                n=event["renamed"],
            )
            if event["auto"]
            else t("notify_renamed", "Files renamed: {n}", n=event["renamed"]),
        ]
        names = [Path(f["to"]).name for f in event["files"]]
        lines += [f"• {name}" for name in names[:MAX_LISTED]]
        if len(names) > MAX_LISTED:
            lines.append(t("notify_more", "…and {n} more", n=len(names) - MAX_LISTED))
        return "\n".join(lines)
