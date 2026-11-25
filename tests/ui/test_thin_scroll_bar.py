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
"""The thin scroll bar: hidden at rest, shown while the content scrolls."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QWidget

from sok.ui.components.thin_scroll_bar import ThinScrollBar, thin_scroll_bar


@pytest.fixture
def area(qtbot):
    area = QScrollArea()
    qtbot.addWidget(area)
    content = QWidget()
    content.setFixedSize(200, 2000)
    area.setWidget(content)
    area.resize(220, 300)
    area.show()
    return area


def test_the_bar_of_the_system_is_hidden(area):
    thin_scroll_bar(area)

    assert area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff


def test_it_shows_while_scrolling_then_fades_out(qtbot, area):
    bar = thin_scroll_bar(area)
    assert bar._opacity == 0

    area.verticalScrollBar().setValue(500)

    qtbot.waitUntil(lambda: bar._opacity == 1.0, timeout=1000)
    qtbot.waitUntil(lambda: bar._opacity == 0.0, timeout=3000)


def test_dragging_it_scrolls_the_content(area):
    bar = thin_scroll_bar(area)
    rect = bar.handle_rect()
    assert rect is not None

    bar._grab = rect.height() / 2
    bar._drag_to(bar.height())  # to the bottom

    scroll = area.verticalScrollBar()
    assert scroll.value() == scroll.maximum()


def test_nothing_to_scroll_no_bar(qtbot):
    area = QScrollArea()
    qtbot.addWidget(area)
    area.setWidget(QWidget())
    area.resize(200, 200)
    area.show()
    bar = area.findChild(ThinScrollBar) or thin_scroll_bar(area)

    bar.wake()

    assert bar.handle_rect() is None
    assert bar._opacity == 0
