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

from typing import Any, Callable, Dict

from sok.core.batch import group_game_files, parse_game
from sok.core.interfaces import ContentType, MediaType
from sok.file_operations import GameFileOperations
from sok.ui.i18n import tr
from sok.ui.pages.batch_page import BatchPage


class GamesPage(BatchPage):
    """Page for batch game renaming.

    A row is one game: a ROM, or the .cue and .bin files and the discs of a
    disc game. A one-file game goes to Platform/ under its online title and
    the tags of its dump; a game of several files goes to
    Platform/Title (Year)/ with its file names kept (see
    GameFileOperations.batch_target).
    """

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

    def empty_hint(self) -> str:
        return tr("games_drop_hint", "Drop game files or folders, or click to browse")

    def add_more_text(self) -> str:
        return tr("add_more_games", "+ Add more games")

    def query_placeholder(self) -> str:
        return tr("game_title", "Game title")
