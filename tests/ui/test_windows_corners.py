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
from PySide6.QtWidgets import QWidget

from sok.ui import main_window, platform
from sok.ui.main_window import MainWindow


def test_corners_are_left_alone_off_windows(qtbot, monkeypatch):
    monkeypatch.setattr(platform, "IS_WINDOWS", False)
    widget = QWidget()
    qtbot.addWidget(widget)

    assert platform.round_native_corners(widget) is False


@pytest.mark.parametrize("is_windows", [True, False])
def test_only_the_windows_window_is_opaque(qtbot, monkeypatch, is_windows):
    # See-through, Windows composed the whole window at each frame of an
    # animation; Linux keeps it to draw its rounded corners.
    monkeypatch.setattr(main_window, "IS_MACOS", False)
    monkeypatch.setattr(main_window, "IS_WINDOWS", is_windows)
    monkeypatch.setattr(main_window, "round_native_corners", lambda _w: True)
    # No update check or Discord: they would outlive the window.
    monkeypatch.setattr(MainWindow, "_setup_services", lambda self: None)
    window = MainWindow()
    qtbot.addWidget(window)

    translucent = window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert translucent is not is_windows
    assert window._close_btn.top_right_radius == (0 if is_windows else 12)


def test_the_window_keys_take_the_ink_of_the_theme(qtbot, monkeypatch):
    # Drawn white whatever the theme, they vanished on the light one. And
    # the four corners are rounded, not only the right ones.
    monkeypatch.setattr(main_window, "IS_MACOS", False)
    monkeypatch.setattr(main_window, "IS_WINDOWS", False)
    monkeypatch.setattr(MainWindow, "_setup_services", lambda self: None)
    window = MainWindow()
    qtbot.addWidget(window)
    window._toggle_theme(False)

    assert window._close_btn.icon_color() == window.c["ink"]
    assert window.c["ink"].upper() != "#FFFFFF"
    window._close_btn._hovered = True
    assert window._close_btn.icon_color() == "#FFFFFF"
    assert "border-radius: 12px;" in window.styleSheet()
