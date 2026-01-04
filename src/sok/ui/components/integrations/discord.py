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
"""
Discord Rich Presence integration for S.O.K Application
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict
from pypresence import Presence, exceptions as rpc_exceptions
import sys
from sok.config import get_config_manager

logger = logging.getLogger(__name__)


class DiscordRPC:
    """Discord Rich Presence manager for S.O.K application."""

    def __init__(self, client_id: Optional[str] = None):
        """
        Initialize Discord RPC manager.

        Args:
            client_id: Discord application client ID
        """
        self.client_id = client_id
        self.presence: Optional[Presence] = None
        self.connected = False
        self.start_time = int(time.time())
        self.current_state: Dict[str, str] = {}

    def connect(self, retries: int = 3) -> bool:
        """
        Connect to Discord.

        Args:
            retries: Number of connection attempts

        Returns:
            True if successfully connected
        """
        if not self.client_id:
            return False

        if self.connected:
            return True

        for attempt in range(retries):
            try:
                self.presence = Presence(self.client_id)
                self.presence.connect()
                self.connected = True
                return True

            except (rpc_exceptions.PyPresenceException, OSError) as exc:
                logger.warning(
                    "Discord RPC connect attempt %s failed", attempt + 1, exc_info=exc
                )
                time.sleep(2)

        return False

    def disconnect(self):
        """Disconnect from Discord."""
        if self.connected and self.presence:
            try:
                self.presence.close()
                self.connected = False
            except (rpc_exceptions.PyPresenceException, OSError) as exc:
                logger.warning("Discord RPC disconnect failed", exc_info=exc)

    def update(
        self,
        state: Optional[str] = None,
        details: Optional[str] = None,
        large_image: str = "logo",
        large_text: str = "S.O.K - Storage Organisation Kit",
        small_image: Optional[str] = None,
        small_text: Optional[str] = None,
        start_timestamp: bool = True,
    ):
        """
        Update Rich Presence status.

        Args:
            state: Application state
            details: Activity details
            large_image: Main image key
            large_text: Main image hover text
            small_image: Small image key
            small_text: Small image hover text
            start_timestamp: Show elapsed time
        """
        if not self.connected or not self.presence:
            return

        try:
            self.presence.update(
                large_image=large_image,
                large_text=large_text,
                state=state,
                details=details,
                small_image=small_image,
                small_text=small_text,
                start=self.start_time if start_timestamp else None,
            )
            self.current_state = {
                "large_image": large_image,
                "large_text": large_text,
                "state": state or "",
                "details": details or "",
                "small_image": small_image or "",
                "small_text": small_text or "",
            }

        except (
            rpc_exceptions.PyPresenceException,
            OSError,
            ValueError,
            TypeError,
        ) as exc:
            logger.warning("Discord RPC update failed", exc_info=exc)

    def set_idle(self):
        """Set status to idle."""
        self.update(
            state="En attente",
            details="Pret a organiser",
            small_image="idle",
            small_text="Idle",
        )

    def set_organizing_videos(self, title: Optional[str] = None):
        """
        Sets the state to organizing videos.

        Args:
            title: Title of the current video
        """
        self.update(
            state="Organizing videos",
            details=title if title else "Processing...",
            small_image="video",
            small_text="Videos",
        )

    def set_organizing_music(self, album: Optional[str] = None):
        """
        Sets the state to organizing music.

        Args:
            album: Name of the current album
        """
        self.update(
            state="Organizing music",
            details=album if album else "Processing...",
            small_image="music",
            small_text="Music",
        )

    def set_organizing_books(self, title: Optional[str] = None):
        """
        Sets the state to organizing books.

        Args:
            title: Title of the current book
        """
        self.update(
            state="Organizing books",
            details=title if title else "Processing...",
            small_image="book",
            small_text="Books",
        )

    def set_organizing_games(self, title: Optional[str] = None):
        """
        Sets the state to organizing games.

        Args:
            title: Name of the current game
        """
        self.update(
            state="Organizing games",
            details=title if title else "Processing...",
            small_image="game",
            small_text="Games",
        )

    def set_searching(self, query: str, media_type: str):
        """
        Sets the state to searching.

        Args:
            query: Search term
            media_type: Media type (video, music, book, game)
        """
        media_icons = {
            "video": "video",
            "music": "music",
            "book": "book",
            "game": "game",
        }

        self.update(
            state=f"Searching for {media_type}",
            details=query,
            small_image=media_icons.get(media_type, "search"),
            small_text="Searching",
        )

    def clear(self):
        """Clears the Rich Presence"""
        if self.connected and self.presence:
            try:
                self.presence.clear()
                self.current_state = {}
            except (rpc_exceptions.PyPresenceException, OSError) as e:
                logger.warning("Discord RPC clear failed", exc_info=e)

    def save_state(self, file_path: Optional[Path] = None):
        """
        Saves the current state to a JSON file

        Args:
            file_path: File path (default: data/discord_rpc.json)
        """
        if file_path is None:
            project_root = Path(__file__).parent.parent
            file_path = project_root / "data" / "discord_rpc.json"

        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.current_state, f, indent=2)
        except (
            OSError,
            ValueError,
            TypeError,
            rpc_exceptions.PyPresenceException,
        ) as e:
            logger.warning("Discord RPC state save failed", exc_info=e)

    def load_state(self, file_path: Optional[Path] = None):
        """
        Loads and applies state from a JSON file

        Args:
            file_path: File path (default: data/discord_rpc.json)
        """
        if file_path is None:
            project_root = Path(__file__).parent.parent
            file_path = project_root / "data" / "discord_rpc.json"

        if not file_path.exists():
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            if self.connected and self.presence:
                self.presence.update(**state)
                self.current_state = state

        except (
            OSError,
            ValueError,
            TypeError,
            rpc_exceptions.PyPresenceException,
        ) as e:
            logger.warning("Discord RPC state load failed", exc_info=e)


class DiscordRPCManager:
    """Singleton manager for Discord RPC"""

    _instance: Optional[DiscordRPC] = None

    @classmethod
    def get_instance(cls, client_id: Optional[str] = None) -> DiscordRPC:
        """
        Gets the singleton instance

        Args:
            client_id: Discord application ID

        Returns:
            DiscordRPC instance
        """
        if cls._instance is None:
            cls._instance = DiscordRPC(client_id)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Resets the singleton instance"""
        if cls._instance:
            cls._instance.disconnect()
        cls._instance = None


def setup_discord_rpc(
    client_id: str, auto_connect: bool = True
) -> Optional[DiscordRPC]:
    """
    Configure and initialize Discord RPC

    Args:
        client_id: Discord application ID
        auto_connect: Connect automatically

    Returns:
        DiscordRPC instance or None if failed
    """

    rpc = DiscordRPCManager.get_instance(client_id)

    if auto_connect:
        if rpc.connect():
            rpc.set_idle()
            return rpc
        return None

    return rpc


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

    config = get_config_manager()
    client_id = config.get("client_id_discord")

    if not client_id:
        print("CLIENT_ID_DISCORD not defined in .env (or config.json)")
        exit(1)

    print("Discord Rich Presence Test")
    print(f"Client ID: {client_id}")

    rpc = setup_discord_rpc(client_id)

    if rpc:
        print("\n1. Idle state")
        rpc.set_idle()
        time.sleep(3)

        print("2. Video organization")
        rpc.set_organizing_videos("Game of Thrones S01E01")
        time.sleep(3)

        print("3. Music organization")
        rpc.set_organizing_music("Daft Punk - Discovery")
        time.sleep(3)

        print("4. Searching")
        rpc.set_searching("Breaking Bad", "video")
        time.sleep(3)

        print("5. Saving state")
        rpc.save_state()

        print("6. Clearing")
        rpc.clear()
        time.sleep(2)

        print("7. Loading state")
        rpc.load_state()
        time.sleep(3)

        print("\nDisconnecting")
        rpc.disconnect()

        print("Test completed!")
    else:
        print("Unable to connect to Discord")
