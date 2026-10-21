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

from sok.apis.games.rawg_api import RAWGApi, clean_title
from sok.core.batch import STATUS_READY, evaluate, parse_game
from sok.core.interfaces import ContentType


@pytest.mark.parametrize(
    "name, platforms, expected",
    [
        ("Pokemon: Emerald Version (GBA)", [], "Pokemon: Emerald Version"),
        ("Super Mario 64 (n64)", [], "Super Mario 64"),
        ("Tetris (Game Boy)", ["Game Boy"], "Tetris"),
        ("Halo: Combat Evolved", ["PC"], "Halo: Combat Evolved"),
        ("Doom (2016)", ["PC"], "Doom (2016)"),
        ("Ys I & II (Chronicles)", [], "Ys I & II (Chronicles)"),
        (None, [], None),
    ],
)
def test_only_a_console_name_is_removed(name, platforms, expected):
    assert clean_title(name, platforms) == expected


def test_search_and_details_give_clean_titles():
    api = RAWGApi()
    game = {
        "id": 1,
        "name": "Pokemon: Emerald Version (GBA)",
        "released": "2004-09-15",
        "platforms": [{"platform": {"name": "Game Boy Advance"}}],
    }

    async def fake_request(endpoint, params):
        return {"results": [game]} if endpoint == "games" else game

    api._make_request = fake_request
    found = asyncio.run(api.search("Pokemon Emerald", ContentType.GAME))
    details = asyncio.run(api.get_details("1", ContentType.GAME))

    assert found["results"][0]["title"] == "Pokemon: Emerald Version"
    assert found["results"][0]["platforms"] == ["Game Boy Advance"]
    assert details["name"] == "Pokemon: Emerald Version"


def test_a_rom_matches_a_title_without_its_console():
    parsed = parse_game([Path("Pokemon - Emerald Version (USA).gba")])
    candidate = {"title": clean_title("Pokemon: Emerald Version (GBA)"), "id": 1}

    assert evaluate(parsed.query, parsed.year, [candidate]) == (0, STATUS_READY)
