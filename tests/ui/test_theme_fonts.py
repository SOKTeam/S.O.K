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
from PySide6.QtGui import QFont, QFontDatabase

from sok.ui.theme import Theme, load_bundled_fonts, ui_font


def test_bundled_fonts_are_registered(qapp):
    load_bundled_fonts()

    families = QFontDatabase.families()
    assert Theme.FONT in families
    assert Theme.MONO in families


def test_ui_font_sets_the_exact_weight(qapp):
    font = ui_font(52, 650)

    assert font.family() == Theme.FONT
    assert font.pixelSize() == 52
    assert font.variableAxisValue(QFont.Tag("wght")) == 650


def test_ui_font_mono_and_tabular_figures(qapp):
    font = ui_font(13, mono=True, tabular=True)

    assert font.family() == Theme.MONO
    assert font.featureValue(QFont.Tag("tnum")) == 1
