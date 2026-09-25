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
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QLabel, QWidget

from sok.ui.theme import Theme, set_tone, tone_stylesheet

PALETTES = [Theme.ORANGE, Theme.MAC_LIGHT, Theme.DARK]


def tone_names(c):
    return {k.removeprefix(Theme.TONE_PREFIX) for k in c if k.startswith("tone_")}


@pytest.fixture
def label(qtbot):
    parents = []

    def make(palette):
        parent = QWidget()
        parent.setStyleSheet(tone_stylesheet(palette))
        qtbot.addWidget(parent)
        parents.append(parent)
        return QLabel("text", parent)

    return make


def text_color(widget):
    widget.ensurePolished()
    return widget.palette().color(QPalette.ColorRole.WindowText)


class TestTones:
    def test_every_palette_defines_the_same_tones(self):
        assert tone_names(Theme.ORANGE) == tone_names(Theme.MAC_LIGHT)
        assert tone_names(Theme.DARK) == tone_names(Theme.MAC_LIGHT)

    @pytest.mark.parametrize("palette", PALETTES)
    def test_tone_colors_the_text(self, label, palette):
        lbl = label(palette)

        set_tone(lbl, "ok")

        assert text_color(lbl) == QColor(palette["tone_ok"])

    def test_clearing_the_tone_restores_the_default_color(self, label):
        lbl = label(Theme.MAC_LIGHT)
        default = text_color(lbl)
        set_tone(lbl, "error")

        set_tone(lbl, None)

        assert text_color(lbl) == default
