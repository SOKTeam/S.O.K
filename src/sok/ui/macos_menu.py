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
"""Native macOS menu bar.

macOS apps are expected to provide a global menu bar with the standard
shortcuts. Qt moves the About, Settings and Quit actions to the
application menu thanks to their menu role.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import QMessageBox

from sok.__version__ import __version__
from sok.config import get_config_manager
from sok.ui.i18n import tr

if TYPE_CHECKING:
    from sok.ui.main_window import MainWindow

DOCUMENTATION_URL = "https://sokteam.github.io/sok"

# Pages reachable with Cmd+1 to Cmd+6, in sidebar order.
PAGE_ACTIONS = [
    ("home", "Home"),
    ("tv_shows", "TV Shows"),
    ("movies", "Movies"),
    ("music", "Music"),
    ("books", "Books"),
    ("games", "Games"),
]
SETTINGS_PAGE = 6

# Qt ships no translation for these codes under the same name.
QT_TRANSLATION_NAMES = {"pt": "pt_BR"}


class MacMenuBar:
    """Build and translate the native menu bar of the main window.

    The window must provide _go(index), _toggle_sidebar() and
    current_page().
    """

    def __init__(self, window: "MainWindow"):
        """Create the menus.

        Args:
            window: Main window owning the menu bar.
        """
        self._window = window
        self._qt_translator: QTranslator | None = None
        self._actions: list[tuple[QAction, str, str]] = []
        self._menus: list = []

        menu_bar = window.menuBar()

        file_menu = self._menu(menu_bar, "menu_file", "File")
        # About, Settings and Quit are moved by Qt to the "S.O.K" menu.
        about = self._action(file_menu, "about_app", "About S.O.K", self._show_about)
        about.setMenuRole(QAction.MenuRole.AboutRole)
        settings = self._action(
            file_menu,
            "settings",
            "Settings",
            lambda: window._go(SETTINGS_PAGE),
            QKeySequence.StandardKey.Preferences,
        )
        settings.setMenuRole(QAction.MenuRole.PreferencesRole)
        quit_action = self._action(
            file_menu,
            "quit",
            "Quit",
            QCoreApplication.quit,
            QKeySequence.StandardKey.Quit,
        )
        quit_action.setMenuRole(QAction.MenuRole.QuitRole)
        self._action(
            file_menu,
            "close_window",
            "Close Window",
            window.close,
            QKeySequence.StandardKey.Close,
        )

        edit_menu = self._menu(menu_bar, "menu_edit", "Edit")
        self._action(
            edit_menu, "find", "Find", self._focus_search, QKeySequence.StandardKey.Find
        )

        view_menu = self._menu(menu_bar, "menu_view", "View")
        self._action(
            view_menu,
            "toggle_sidebar",
            "Show/Hide Sidebar",
            window._toggle_sidebar,
            QKeySequence("Ctrl+Meta+S"),
        )
        view_menu.addSeparator()
        for index, (key, default) in enumerate(PAGE_ACTIONS):
            self._action(
                view_menu,
                key,
                default,
                lambda _=False, i=index: window._go(i),
                QKeySequence(f"Ctrl+{index + 1}"),
            )
        view_menu.addSeparator()
        self._action(
            view_menu,
            "full_screen",
            "Enter Full Screen",
            self._toggle_full_screen,
            QKeySequence.StandardKey.FullScreen,
        )

        window_menu = self._menu(menu_bar, "menu_window", "Window")
        self._action(
            window_menu,
            "minimize",
            "Minimize",
            window.showMinimized,
            QKeySequence("Ctrl+M"),
        )
        self._action(window_menu, "zoom", "Zoom", self._toggle_zoom)

        help_menu = self._menu(menu_bar, "menu_help", "Help")
        self._action(
            help_menu,
            "documentation",
            "S.O.K Documentation",
            lambda: QDesktopServices.openUrl(QUrl(DOCUMENTATION_URL)),
        )

        self.retranslate()

    def _menu(self, menu_bar, key: str, default: str):
        """Add a translatable top-level menu."""
        menu = menu_bar.addMenu(tr(key, default))
        self._menus.append((menu, key, default))
        return menu

    def _action(self, menu, key: str, default: str, slot, shortcut=None) -> QAction:
        """Add a translatable action to a menu."""
        action = QAction(tr(key, default), self._window)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        menu.addAction(action)
        self._actions.append((action, key, default))
        return action

    def retranslate(self) -> None:
        """Apply the current language to every menu and action."""
        self._install_qt_translator()
        for menu, key, default in self._menus:
            menu.setTitle(tr(key, default))
        for action, key, default in self._actions:
            action.setText(tr(key, default))

    def _install_qt_translator(self) -> None:
        """Translate the menu items that Qt generates (Hide, Services...)."""
        app = QCoreApplication.instance()
        if app is None:
            return
        if self._qt_translator is not None:
            app.removeTranslator(self._qt_translator)
            self._qt_translator = None

        lang = get_config_manager().get("language", "en")
        if lang == "en":
            return
        translator = QTranslator(app)
        name = QT_TRANSLATION_NAMES.get(lang, lang)
        path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if translator.load(f"qtbase_{name}", path):
            app.installTranslator(translator)
            self._qt_translator = translator

    def _show_about(self) -> None:
        QMessageBox.about(
            self._window,
            tr("about_app", "About S.O.K"),
            f"<b>S.O.K</b> {__version__}<br>"
            f"{tr('app_description', 'Storage Organisation Kit')}",
        )

    def _focus_search(self) -> None:
        focus_search = getattr(self._window.current_page(), "focus_search", None)
        if callable(focus_search):
            focus_search()

    def _toggle_full_screen(self) -> None:
        if self._window.isFullScreen():
            self._window.showNormal()
        else:
            self._window.showFullScreen()

    def _toggle_zoom(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()
