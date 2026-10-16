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
"""Application update management.

Provides functionality to check for updates from GitHub releases,
download new versions, and manage the update installation process.
"""

import os
import platform
import sys
import aiohttp
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from packaging import version
from sok import __version__ as current_version
import requests
import tempfile
import subprocess

logger = logging.getLogger(__name__)


def running_appimage() -> Optional[Path]:
    """Return the AppImage file the app runs from (Linux), else None.

    The AppImage runtime sets APPIMAGE to the path of the file.
    """
    if not sys.platform.startswith("linux"):
        return None
    path = os.environ.get("APPIMAGE")
    return Path(path) if path else None


class UpdateManager:
    """
    Manages update verification and retrieval via GitHub Releases.
    """

    GITHUB_REPO = "SOKTeam/S.O.K"
    API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    def __init__(self):
        """Initialize the update manager.

        Sets up the manager with no cached release data.
        """
        self.latest_release: Optional[Dict[str, Any]] = None

    async def check_for_updates(self) -> Tuple[bool, Optional[str]]:
        """
        Check if an update is available.

        Returns:
            Tuple[bool, str]: (Is there an update?, Detected version)
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.API_URL, timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        tag_name = data.get("tag_name", "").lstrip("v")

                        if not tag_name:
                            return False, None

                        if version.parse(tag_name) > version.parse(current_version):
                            self.latest_release = data
                            return True, tag_name

            return False, None

        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            logger.error("Error checking for updates", exc_info=exc)
            return False, None

    def get_release_notes(self) -> str:
        """Return the changelog for the latest release."""
        if self.latest_release:
            return self.latest_release.get("body", "Aucune information disponible.")
        return ""

    def get_download_url(self) -> Optional[str]:
        """
        Get the download URL of the installer for this platform.
        Windows: the setup .exe first, then any .exe. macOS: the .dmg.
        Linux: the AppImage of this architecture, when running from an
        AppImage (it replaces itself). Falls back to the release page.
        """
        if not self.latest_release:
            return None

        assets = self.latest_release.get("assets", [])
        if sys.platform.startswith("linux"):
            suffix = f"_{platform.machine()}.appimage"
            if running_appimage():
                for asset in assets:
                    if asset.get("name", "").lower().endswith(suffix):
                        return asset.get("browser_download_url")
            return self.latest_release.get("html_url")

        if sys.platform == "darwin":
            for asset in assets:
                if asset.get("name", "").lower().endswith(".dmg"):
                    return asset.get("browser_download_url")
            return self.latest_release.get("html_url")

        for asset in assets:
            name = asset.get("name", "").lower()
            if name.endswith(".exe") and "setup" in name:
                return asset.get("browser_download_url")

        for asset in assets:
            if asset.get("name", "").lower().endswith(".exe"):
                return asset.get("browser_download_url")

        return self.latest_release.get("html_url")

    @staticmethod
    def _download(url: str, target_path, progress_callback=None):
        """Download url to target_path, reporting the percentage done."""
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_length = int(r.headers.get("content-length", 0))
            dl = 0

            with open(target_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        dl += len(chunk)
                        f.write(chunk)
                        if progress_callback and total_length > 0:
                            percent = int((dl / total_length) * 100)
                            progress_callback(percent)

    def replace_appimage(self, url: str, progress_callback=None) -> None:
        """Download the new AppImage over the one the app runs from.

        The file keeps its path, so launchers and shortcuts still work. It
        is downloaded next to it, then renamed: the swap is atomic, and the
        running app keeps the old file open until it quits.

        Raises:
            OSError: The folder is not writable or the download failed.
        """
        current = running_appimage()
        if current is None:
            raise OSError("S.O.K is not running from an AppImage")
        partial = current.with_name(current.name + ".part")
        try:
            self._download(url, partial, progress_callback)
            partial.chmod(0o755)
            os.replace(partial, current)
        except (requests.RequestException, OSError) as exc:
            partial.unlink(missing_ok=True)
            logger.error("Error replacing the AppImage", exc_info=exc)
            raise OSError(str(exc)) from exc

    @staticmethod
    def restart_appimage() -> None:
        """Start the updated AppImage; the caller then quits the app."""
        current = running_appimage()
        if current is not None:
            subprocess.Popen([str(current)], start_new_session=True)

    def download_and_install(self, url: str, progress_callback=None):
        """
        Download the installer and launch it (on macOS, open the disk image;
        on Linux, replace the AppImage). The caller then quits the app: this
        runs in a worker thread, where sys.exit() would only end the thread.
        """
        if running_appimage():
            self.replace_appimage(url, progress_callback)
            return

        try:
            temp_dir = tempfile.gettempdir()
            installer = (
                "SOK_Update.dmg" if sys.platform == "darwin" else "SOK_Setup_Update.exe"
            )
            target_path = os.path.join(temp_dir, installer)

            self._download(url, target_path, progress_callback)

            if sys.platform == "darwin":
                # Mounts the disk image in the Finder, where the user drags
                # the new app over the old one.
                subprocess.Popen(["open", target_path])
            else:
                subprocess.Popen([target_path])

        except (requests.RequestException, OSError, ValueError) as exc:
            logger.error("Error downloading update", exc_info=exc)
            raise
