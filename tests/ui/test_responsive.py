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
"""Sizes that follow the size of the window."""

from PySide6.QtWidgets import QWidget

from sok.ui.responsive import (
    MAX_CONTENT_WIDTH,
    CenteredColumn,
    display_px,
    side_width,
)


def test_the_right_column_takes_a_third_within_bounds():
    assert side_width(850) == 320
    assert side_width(1100) == 396
    assert side_width(5120) == 520


def test_the_big_titles_get_smaller_in_a_narrow_page():
    assert display_px(1440) == 52
    assert display_px(850) == 40
    # In between, the size follows the width without a jump.
    sizes = [display_px(w) for w in range(850, 1200)]
    assert all(0 <= b - a <= 1 for a, b in zip(sizes, sizes[1:]))


def test_the_decorations_fade_out_little_by_little():
    from sok.ui.responsive import FADE_BAND, presence

    assert presence(800, 620) == 1.0
    assert presence(500, 620) == 0.0
    assert presence(620, 620) == 0.5
    assert 0 < presence(620 + FADE_BAND // 4, 620) < 1


def test_the_content_is_centered_past_its_widest(qtbot):
    child = QWidget()
    column = CenteredColumn(child)
    qtbot.addWidget(column)
    column.show()

    column.resize(1200, 600)
    assert child.geometry().x() == 0 and child.width() == 1200

    column.resize(5120, 600)
    assert child.width() == MAX_CONTENT_WIDTH
    assert child.geometry().x() == (5120 - MAX_CONTENT_WIDTH) // 2
