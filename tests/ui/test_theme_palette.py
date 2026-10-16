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

from sok.ui.main_window import MainWindow
from sok.ui.theme import Theme

Role = QPalette.ColorRole


@pytest.mark.parametrize("theme", [Theme.DARK, Theme.ORANGE, Theme.MAC_LIGHT])
def test_text_roles_use_the_theme_text_color(qapp, theme):
    pal = MainWindow._theme_palette(theme)

    for role in (Role.WindowText, Role.Text, Role.ButtonText):
        assert pal.color(role) == QColor(theme["text"])
    assert pal.color(Role.Window) == QColor(theme["bg"])


def test_disabled_text_is_dimmed(qapp):
    pal = MainWindow._theme_palette(Theme.DARK)

    disabled = pal.color(QPalette.ColorGroup.Disabled, Role.Text)
    assert disabled == QColor(Theme.DARK["tertiary"])
