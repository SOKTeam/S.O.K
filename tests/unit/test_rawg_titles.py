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
    "name, platforms, released, expected",
    [
        ("Pokemon: Emerald Version (GBA)", [], None, "Pokemon: Emerald Version"),
        ("Super Mario 64 (n64)", [], None, "Super Mario 64"),
        ("Tetris (Game Boy)", ["Game Boy"], None, "Tetris"),
        ("Halo: Combat Evolved", ["PC"], None, "Halo: Combat Evolved"),
        ("DOOM (2016)", ["PC"], "2016-05-12", "DOOM"),
        ("Doom (2016)", ["PC"], None, "Doom (2016)"),
        ("Doom (2016)", ["PC"], "1993-12-10", "Doom (2016)"),
        ("Pac-Man (1980) (GBA)", [], "1980-05-22", "Pac-Man"),
        ("Ys I & II (Chronicles)", [], None, "Ys I & II (Chronicles)"),
        (None, [], None, None),
    ],
)
def test_only_a_console_or_the_release_year_is_removed(
    name, platforms, released, expected
):
    assert clean_title(name, platforms, released) == expected


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


def test_a_title_with_its_year_matches_the_plain_name():
    parsed = parse_game([Path("Doom (Europe).iso")])
    candidate = {
        "title": clean_title("DOOM (2016)", ["PC"], "2016-05-12"),
        "release_date": "2016-05-12",
    }

    assert evaluate(parsed.query, parsed.year, [candidate]) == (0, STATUS_READY)
