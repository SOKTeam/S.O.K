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
import asyncio
from pathlib import Path

import pytest

from sok.core.batch import BatchMatcher, group_game_files, parse_game
from sok.core.exceptions import APIAuthenticationError, APIRateLimitError
from sok.core.interfaces import ContentType
from sok.file_operations import GameFileOperations
from sok.media.games.game import Game
from sok.ui.factories.media_factory import create_media_item


def game(title, date="1996-09-09"):
    item = Game(title, "en", None, platform="")
    item.release_date = date
    return item


def test_files_of_one_game_are_grouped():
    files = [
        Path("/g/Final Fantasy VII (USA) (Disc 1).cue"),
        Path("/g/Final Fantasy VII (USA) (Disc 2).bin"),
        Path("/g/Crash Bandicoot (USA).cue"),
        Path("/g/Crash Bandicoot (USA) (Track 2).bin"),
        Path("/g/Super Mario World (USA).sfc"),
        Path("/other/Super Mario World (USA).sfc"),
    ]

    groups = group_game_files(files)

    assert [len(g) for g in groups] == [2, 2, 1, 1]


def test_game_query_leaves_the_tags_out():
    assert parse_game([Path("[SNES] Chrono Trigger (USA) (Rev 1).smc")]).query == (
        "Chrono Trigger"
    )


def test_one_file_game_keeps_the_tags_of_its_dump():
    ops = GameFileOperations()
    name = ops.generate_new_filename(
        game("Super Mario World"), "super mario world (USA) (Rev 1) [SNSP-MW].sfc"
    )
    assert name == "Super Mario World (USA) (Rev 1) [SNSP-MW].sfc"


def test_platform_comes_from_tag_extension_or_folder():
    ops = GameFileOperations()
    assert ops.detect_platform(Path("/x/[SNES] Chrono Trigger.smc")) == "Super Nintendo"
    assert ops.detect_platform(Path("/x/Pokemon Emerald.gba")) == "Game Boy Advance"
    assert ops.detect_platform(Path("/roms/PS1/Crash Bandicoot.cue")) == "PlayStation"
    assert ops.detect_platform(Path("/downloads/Halo.iso")) is None


def test_batch_renames_roms_and_keeps_disc_games_whole(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    rom = src / "super mario world (USA).sfc"
    cue = src / "Crash Bandicoot (USA).cue"
    bin_ = src / "Crash Bandicoot (USA).bin"
    for f in (rom, cue, bin_):
        f.write_text("x")
    crash = game("Crash Bandicoot")

    report = GameFileOperations().organize_items_batch(
        [(rom, game("Super Mario World")), (cue, crash), (bin_, crash)],
        str(tmp_path / "out"),
    )

    out = tmp_path / "out"
    assert report["total_moved"] == 3
    assert (out / "Super Nintendo/Super Mario World (USA).sfc").exists()
    assert (out / "Crash Bandicoot (1996)/Crash Bandicoot (USA).cue").exists()
    assert (out / "Crash Bandicoot (1996)/Crash Bandicoot (USA).bin").exists()


def test_factory_keeps_the_year_and_no_default_platform():
    item = create_media_item(
        {"id": 1, "title": "Halo", "release_date": "2001-11-15"}, "game", manager=None
    )
    assert item.get_formatted_name() == "Halo (2001)"


class FailingManager:
    def __init__(self, error):
        self.error = error

    async def search(self, query, content_type, **kwargs):
        raise self.error


@pytest.mark.parametrize(
    "error",
    [APIAuthenticationError("RAWG: HTTP 401"), APIRateLimitError("quota", "x")],
)
def test_a_missing_key_or_quota_stops_the_batch(error):
    matcher = BatchMatcher(FailingManager(error), ContentType.GAME, parse_game)

    with pytest.raises(type(error)):
        asyncio.run(matcher.match_all([[Path("Halo.iso")], [Path("Doom.iso")]]))


def test_game_format_of_the_settings_is_used(monkeypatch):
    from sok.file_operations import game_operations

    class Config:
        def get(self, key, default=None):
            if key == "game_format":
                return "{title} ({year}) [{platform}] {tags}"
            return default

    monkeypatch.setattr(game_operations, "get_config_manager", lambda: Config())
    item = game("Super Mario World", "1990-11-21")

    assert (
        GameFileOperations().generate_new_filename(item, "smw (USA).sfc")
        == "Super Mario World (1990) [Super Nintendo] (USA).sfc"
    )
