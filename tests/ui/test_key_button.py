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
from PySide6.QtGui import QColor

from sok.ui.components.base import KeyButton
from sok.ui.theme import Theme


def pixel(widget, x, y):
    return widget.grab().toImage().pixelColor(x, y)


def test_heights_include_the_shadow_line(qtbot):
    regular, small = KeyButton("Rename"), KeyButton("Go", small=True)
    qtbot.addWidget(regular)
    qtbot.addWidget(small)

    assert regular.height() == 45
    assert small.height() == 33


def test_count_and_shortcut_widen_the_button(qtbot):
    btn = KeyButton("Rename the movies", primary=True)
    qtbot.addWidget(btn)
    plain = btn.sizeHint().width()

    btn.set_count(18)
    btn.set_shortcut("⌘R")

    assert btn.sizeHint().width() > plain


def test_faces_use_the_tokens(qtbot):
    primary, secondary = KeyButton("A", primary=True), KeyButton("B")
    for btn in (primary, secondary):
        qtbot.addWidget(btn)
        btn.resize(btn.sizeHint())

    middle = 22
    assert pixel(primary, 4, middle) == QColor(Theme.DARK["accent"])
    assert pixel(secondary, 4, middle) == QColor(Theme.DARK["key"])


def test_pressed_face_is_darker(qtbot):
    btn = KeyButton("A")
    qtbot.addWidget(btn)
    btn.resize(btn.sizeHint())

    btn.setDown(True)

    assert pixel(btn, 10, 22) == QColor(Theme.DARK["key-pressed"])
