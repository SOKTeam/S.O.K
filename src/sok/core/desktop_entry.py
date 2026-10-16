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
"""Desktop integration of the Linux AppImage.

GNOME and KDE show an app's icon and name only through an installed
.desktop file matching its id (on Wayland they ignore the window icon). An
AppImage installs nothing, so S.O.K adds its own entry to the user's
applications menu each time it starts from one.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from sok.config.config_manager import xdg_base
from sok.core.updater import running_appimage

logger = logging.getLogger(__name__)

APP_ID = "com.sokteam.sok"


def _string_value(text: str) -> str:
    """Escape backslashes, as desktop entry string values require."""
    return text.replace("\\", "\\\\")


def exec_argument(path: Path) -> str:
    """Quote a path for the Exec key of a desktop entry.

    The Desktop Entry Specification quotes with double quotes (not the
    shell's single quotes), escapes ", `, $ and \\ inside them and doubles
    % (field codes); string escaping then applies to the whole value.
    """
    text = str(path).replace("%", "%%")
    for char in '\\"`$':
        text = text.replace(char, "\\" + char)
    return _string_value(f'"{text}"')


def desktop_entry(template: str, appimage: Path) -> str:
    """Point the packaged desktop entry at the AppImage file.

    Args:
        template: packaging/linux/com.sokteam.sok.desktop, as bundled.
        appimage: Path of the AppImage the app runs from.

    Returns:
        The entry with Exec running the AppImage, and TryExec hiding it from
        the menu once the file is gone.
    """
    lines = []
    for line in template.splitlines():
        if line.startswith("Exec="):
            lines.append(f"Exec={exec_argument(appimage)}")
            lines.append(f"TryExec={_string_value(str(appimage))}")
        elif not line.startswith("TryExec="):
            lines.append(line)
    return "\n".join(lines) + "\n"


def _write_if_changed(path: Path, data: bytes) -> None:
    """Write data to path unless it already holds it."""
    if path.exists() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def install_desktop_entry(appdir: Optional[Path] = None) -> None:
    """Add S.O.K to the applications menu when it runs from an AppImage.

    Writes the entry and its icon to the XDG data folder (~/.local/share),
    refreshed on each start so the entry follows the AppImage if it moves.
    Failures are logged, never raised: the app starts anyway.

    Args:
        appdir: Mounted AppImage contents; defaults to $APPDIR, set by the
            AppImage runtime.
    """
    appimage = running_appimage()
    appdir = appdir or Path(os.environ.get("APPDIR", ""))
    if appimage is None or not appdir.is_dir():
        return
    try:
        template = (appdir / f"{APP_ID}.desktop").read_text(encoding="utf-8")
        data = xdg_base("XDG_DATA_HOME", ".local/share")
        _write_if_changed(
            data / "applications" / f"{APP_ID}.desktop",
            desktop_entry(template, appimage).encode("utf-8"),
        )
        _write_if_changed(
            data / "icons" / "hicolor" / "512x512" / "apps" / f"{APP_ID}.png",
            (appdir / f"{APP_ID}.png").read_bytes(),
        )
    except OSError as exc:
        logger.warning("Could not add S.O.K to the applications menu", exc_info=exc)
