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
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from sok.ui import main_window
from sok.ui.main_window import MainWindow


class FakeWindow(QMainWindow):
    _header_height = staticmethod(MainWindow._header_height)

    def __init__(self):
        super().__init__()
        self._toggle_maximize = MagicMock()


class ShownWindowSpy(QObject):
    """Record every top-level widget shown while installed."""

    def __init__(self):
        super().__init__()
        self.shown = []

    def eventFilter(self, obj, event):
        if (
            event.type() == QEvent.Type.Show
            and isinstance(obj, QWidget)
            and obj.isWindow()
        ):
            self.shown.append(type(obj).__name__)
        return False


@pytest.mark.parametrize("is_macos", [False, True])
def test_building_the_header_opens_no_stray_window(qtbot, monkeypatch, is_macos):
    monkeypatch.setattr(main_window, "IS_MACOS", is_macos)
    window = FakeWindow()
    qtbot.addWidget(window)
    spy = ShownWindowSpy()
    app = QApplication.instance()
    app.installEventFilter(spy)
    try:
        header = MainWindow._build_header(window)
    finally:
        app.removeEventFilter(spy)
    header.setParent(window)

    assert spy.shown == []
    assert window._title_label.isHidden() is is_macos
