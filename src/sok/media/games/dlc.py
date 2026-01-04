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
DLC class for downloadable content and game expansions.
"""

from typing import Optional
from sok.media.games.game import Game


class DLC(Game):
    """
    Class for managing game DLCs and expansions.

    Extends Game class with DLC-specific attributes.

    Additional Attributes:
    ----------------------
        base_game (str): Parent game title
        base_game_id (str): Parent game ID
        dlc_type (str): Type (expansion, cosmetic, season pass, etc.)
        file_size (int): Download size in MB

    Example:
    --------
        >>> manager = UniversalMediaManager()
        >>> dlc = DLC("Blood and Wine", "en", manager, platform="PC")
        >>> dlc.base_game = "The Witcher 3: Wild Hunt"
        >>> dlc.dlc_type = "expansion"
    """

    def __init__(self, name: str, language: str, media_manager, platform: str = "PC"):
        """Initialize a DLC instance."""
        super().__init__(name, language, media_manager, platform)
        self.base_game: Optional[str] = None
        self.base_game_id: Optional[str] = None
        self.dlc_type: str = "expansion"
        self.file_size: int = 0

    def get_formatted_name(self) -> str:
        """Returns formatted DLC name with base game."""
        if self.base_game:
            return f"{self.base_game} - {self.title}"
        return super().get_formatted_name()
