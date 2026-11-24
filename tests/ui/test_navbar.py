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
from PySide6.QtCore import Qt

from sok.ui.components.nav import NavBar


@pytest.fixture
def bar(qtbot):
    bar = NavBar(0, [(2, "Movies"), (1, "TV Shows")], [(7, "history"), (6, "settings")])
    qtbot.addWidget(bar)
    bar.show()
    return bar


def test_clicks_open_their_page(qtbot, bar):
    pages = []
    bar.navigate.connect(pages.append)

    qtbot.mouseClick(bar.words[1], Qt.MouseButton.LeftButton)
    qtbot.mouseClick(bar.mark, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(bar.icons[6], Qt.MouseButton.LeftButton)

    assert pages == [1, 0, 6]


def test_only_the_current_page_is_active(bar):
    bar.set_current(2)

    assert bar.words[2].is_active()
    assert not bar.words[1].is_active()


def test_count_widens_the_word(bar):
    word = bar.words[2]
    plain = word.sizeHint().width()

    bar.set_count(2, 18)

    assert word.sizeHint().width() > plain
