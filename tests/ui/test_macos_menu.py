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
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMainWindow, QWidget

from sok.ui import macos_menu
from sok.ui.macos_menu import MacMenuBar


class FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


class FakeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._go = MagicMock()
        self._toggle_sidebar = MagicMock()
        self.page = QWidget()
        self.page.focus_search = MagicMock()

    def current_page(self):
        return self.page


@pytest.fixture
def config(monkeypatch):
    cfg = FakeConfig(language="en")
    monkeypatch.setattr(macos_menu, "get_config_manager", lambda: cfg)
    return cfg


@pytest.fixture
def window(qtbot, config):
    win = FakeWindow()
    qtbot.addWidget(win)
    win.mac_menu = MacMenuBar(win)
    return win


def action_with_shortcut(window, sequence):
    for action in window.findChildren(QAction):
        if action.shortcut() == QKeySequence(sequence):
            return action
    raise AssertionError(f"No action for {sequence}")


class TestMacMenuBar:
    def test_app_menu_actions_have_their_role(self, window):
        roles = {a.menuRole() for a in window.findChildren(QAction)}

        assert QAction.MenuRole.AboutRole in roles
        assert QAction.MenuRole.PreferencesRole in roles
        assert QAction.MenuRole.QuitRole in roles

    def test_page_shortcuts(self, window):
        action_with_shortcut(window, "Ctrl+2").trigger()
        action_with_shortcut(window, QKeySequence.StandardKey.Preferences).trigger()

        assert [c.args for c in window._go.call_args_list] == [(1,), (6,)]

    def test_find_focuses_the_page_search(self, window):
        action_with_shortcut(window, QKeySequence.StandardKey.Find).trigger()

        window.page.focus_search.assert_called_once()

    def test_qt_menus_follow_the_app_language(self, window, config):
        config._values["language"] = "fr"
        window.mac_menu.retranslate()

        assert QCoreApplication.translate("MAC_APPLICATION_MENU", "Quit %1") == (
            "Quitter %1"
        )

        config._values["language"] = "en"
        window.mac_menu.retranslate()

        assert QCoreApplication.translate("MAC_APPLICATION_MENU", "Quit %1") == (
            "Quit %1"
        )
