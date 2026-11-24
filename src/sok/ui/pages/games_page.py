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
"""Page for batch-renaming games, each with its own online game."""

from typing import Any, Callable, Dict, List, Tuple

from sok.core.batch import group_game_files, parse_game
from sok.core.interfaces import ContentType, MediaType
from sok.file_operations import GameFileOperations
from sok.ui.i18n import tr, trn
from sok.ui.components.scene import Shape
from sok.ui.pages.batch_page import BatchPage


# Short name of each console S.O.K reads in a file name or an extension,
# by maker, for the empty screen. Every value of GameFileOperations.PLATFORMS
# has one (checked by the tests).
CONSOLES: Dict[str, str] = {
    "Nintendo Entertainment System": "NES",
    "Super Nintendo": "SNES",
    "Nintendo 64": "N64",
    "GameCube": "GameCube",
    "Wii": "Wii",
    "Wii U": "Wii U",
    "Nintendo Switch": "Switch",
    "Game Boy": "Game Boy",
    "Game Boy Color": "GBC",
    "Game Boy Advance": "GBA",
    "Nintendo DS": "DS",
    "Nintendo 3DS": "3DS",
    "PlayStation": "PlayStation",
    "PlayStation 2": "PS2",
    "PlayStation 3": "PS3",
    "PlayStation 4": "PS4",
    "PlayStation 5": "PS5",
    "PlayStation Portable": "PSP",
    "PlayStation Vita": "PS Vita",
    "Sega Mega Drive": "Mega Drive",
    "Sega Genesis": "Genesis",
    "Sega CD": "Sega CD",
    "Sega 32X": "32X",
    "Game Gear": "Game Gear",
    "Sega Saturn": "Saturn",
    "Sega Dreamcast": "Dreamcast",
    "Xbox": "Xbox",
    "Xbox 360": "Xbox 360",
    "Xbox One": "Xbox One",
    "Xbox Series X/S": "Xbox Series",
    "PC": "PC",
    "DOS": "DOS",
    "Arcade": "Arcade",
    "MAME": "MAME",
}


class GamesPage(BatchPage):
    """Page for batch game renaming.

    A row is one game: a ROM, or the .cue and .bin files and the discs of a
    disc game. A one-file game goes to Platform/ under its online title and
    the tags of its dump; a game of several files goes to
    Platform/Title (Year)/ with its file names kept (see
    GameFileOperations.batch_target).
    """

    kind = "games"
    scene_shape = Shape.POSTER
    # Square places on the empty screen, as in its mockup.
    empty_shape = Shape.COVER
    default_path_type = "game"
    media_type = MediaType.GAME
    content_type = ContentType.GAME
    factory_type = "game"
    parse = staticmethod(parse_game)
    group_files = staticmethod(group_game_files)

    def make_ops(self) -> GameFileOperations:
        return GameFileOperations()

    def organize_method(self) -> Callable[..., Dict[str, Any]]:
        return self._ops.organize_items_batch

    def page_title(self) -> str:
        return tr("games", "Games")

    def query_placeholder(self) -> str:
        return tr("game_title", "Game title")

    def known_tags(self) -> Tuple[str, List[str]]:
        """The consoles S.O.K recognizes, by their short names."""
        consoles = list(CONSOLES.values())
        label = trn(
            "batch_consoles_known",
            len(consoles),
            "{n} console recognized",
            "{n} consoles recognized",
        )
        return label, consoles
