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
import pytest

from sok.ui import tokens
from sok.ui.theme import Theme


@pytest.mark.parametrize("colors", [tokens.DARK, tokens.LIGHT])
def test_aliases_are_resolved(colors):
    assert not [v for v in colors.values() if v.startswith("{")]


def test_both_themes_have_the_same_tokens():
    assert tokens.DARK.keys() == tokens.LIGHT.keys()


@pytest.mark.parametrize(
    "theme, colors", [(Theme.DARK, tokens.DARK), (Theme.LIGHT, tokens.LIGHT)]
)
def test_text_on_the_accent_is_near_black(theme, colors):
    # White on the coral is only 3:1.
    assert theme["accent"] == colors["sok"]
    assert theme["accent_text"] == colors["on-sok"]
