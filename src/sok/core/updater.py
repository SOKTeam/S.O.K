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
import sys
import aiohttp
import logging
from typing import Optional, Dict, Any, Tuple
from packaging import version
from sok import __version__ as current_version
import requests
import tempfile
import subprocess

logger = logging.getLogger(__name__)


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
        Get the download URL for the Windows installer (.exe).
        Prioritizes files ending with .exe.
        """
        if not self.latest_release:
            return None

        assets = self.latest_release.get("assets", [])
        for asset in assets:
            name = asset.get("name", "").lower()
            if name.endswith(".exe") and "setup" in name:
                return asset.get("browser_download_url")

        for asset in assets:
            if asset.get("name", "").lower().endswith(".exe"):
                return asset.get("browser_download_url")

        return self.latest_release.get("html_url")

    def download_and_install(self, url: str, progress_callback=None):
        """
        Download the installer and launch it.
        """

        try:
            temp_dir = tempfile.gettempdir()
            target_path = os.path.join(temp_dir, "SOK_Setup_Update.exe")

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

            subprocess.Popen([target_path])
            sys.exit(0)

        except (requests.RequestException, OSError, ValueError) as exc:
            logger.error("Error downloading update", exc_info=exc)
            raise
