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
"""
S.O.K - Main Interface
Orange / Frameless / Modern Style
"""

import sys
from ctypes.wintypes import MSG

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QFrame,
    QApplication,
    QSizePolicy,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt,
    QTimer,
    QVariantAnimation,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtGui import QIcon

from sok.ui.theme import Theme, ASSETS_DIR
from sok.ui.components.sidebar import SidebarButton
from sok.ui.components.window import WindowControlButton
from sok.ui.controllers.window_chrome import hit_test_resize
from sok.ui.pages.home_page import HomePage
from sok.ui.pages.organize_page import OrganizePage
from sok.ui.pages.settings_page import SettingsPage
from sok.ui.components.integrations.discord import setup_discord_rpc
from sok.ui.components.integrations.updates import check_and_show_updates
from sok.config import get_config_manager
from sok.ui.i18n import tr, reload_language


class MainWindow(QMainWindow):
    """Main application window for S.O.K.

    Frameless window with custom chrome, sidebar navigation,
    and page stack for organizing media files.

    Attributes:
        dark: Whether dark theme is active.
        c: Current color theme dictionary.
        rpc: Discord Rich Presence instance (if enabled).
    """

    def __init__(self):
        """Initialize the main application window.

        Sets up theme, window properties, and builds the UI.
        """
        super().__init__()

        self._config = get_config_manager()
        theme_pref = self._config.get("theme", "orange")

        self.dark = theme_pref == "dark"
        self.c = Theme.DARK if self.dark else Theme.LIGHT
        self._theme_name = theme_pref

        self._drag_pos = None
        self._restore_rect = None

        self._setup_window()
        self._build()
        self._style()
        self._setup_services()

    def _setup_window(self):
        """Configure window properties.

        Sets title, size, flags for frameless window, and icon.
        """
        self.setWindowTitle("S.O.K")
        self.resize(950, 680)
        self.setMinimumSize(850, 550)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        icon = ASSETS_DIR / "logo.ico"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

    def _setup_services(self):
        """Initialize optional services.

        Sets up Discord Rich Presence and update checker if enabled.
        """
        if self._config.get("use_discord_rpc"):
            self.rpc = setup_discord_rpc(
                self._config.get("client_id_discord"), auto_connect=True
            )
        else:
            self.rpc = None

        if self._config.get("check_updates"):
            QTimer.singleShot(2000, lambda: check_and_show_updates(self))

    def _build(self):
        """Build the main window layout.

        Creates central widget with sidebar and content area.
        """
        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self._sidebar = self._build_sidebar()
        main_layout.addWidget(self._sidebar)

        right_col = self._build_right_column()
        main_layout.addWidget(right_col, 1)

        self._nav[0].setChecked(True)
        self._go(0)

        self.setMouseTracking(True)
        central.setMouseTracking(True)
        self._resize_margin = 5
        self._resize_dir = None
        self._drag_pos = None

    def _build_sidebar(self) -> QWidget:
        """Build the navigation sidebar.

        Returns:
            Configured sidebar widget with navigation buttons.
        """
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        self._sidebar_expanded = True
        self._sidebar_labels = []
        self._nav = []

        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 12)
        sb_layout.setSpacing(0)

        self._menu_btn = SidebarButton("", "menu")
        self._menu_btn.clicked.connect(self._toggle_sidebar)
        sb_layout.addWidget(self._menu_btn)

        self.lbl_library = QLabel(tr("library", "Library"))
        self.lbl_library.setObjectName("SidebarSection")
        section1_effect = QGraphicsOpacityEffect(self.lbl_library)
        section1_effect.setOpacity(1.0)
        self.lbl_library.setGraphicsEffect(section1_effect)
        self._sidebar_labels.append(section1_effect)
        sb_layout.addWidget(self.lbl_library)

        home_btn = SidebarButton(tr("home", "Home"), "home")
        home_btn.clicked.connect(lambda: self._go(0))
        sb_layout.addWidget(home_btn)
        self._nav.append(home_btn)

        for text_key, icon_name, idx in [
            ("videos", "video", 1),
            ("music", "music", 2),
            ("books", "book", 3),
            ("games", "game", 4),
        ]:
            default_text = {
                "videos": "Videos",
                "music": "Music",
                "books": "Books",
                "games": "Games",
            }[text_key]
            btn = SidebarButton(tr(text_key, default_text), icon_name)
            btn.clicked.connect(lambda _, i=idx: self._go(i))
            sb_layout.addWidget(btn)
            self._nav.append(btn)

        sb_layout.addStretch()

        self.lbl_general = QLabel(tr("general", "General"))
        self.lbl_general.setObjectName("SidebarSection")
        section2_effect = QGraphicsOpacityEffect(self.lbl_general)
        section2_effect.setOpacity(1.0)
        self.lbl_general.setGraphicsEffect(section2_effect)
        self._sidebar_labels.append(section2_effect)
        sb_layout.addWidget(self.lbl_general)

        settings_btn = SidebarButton(tr("settings", "Settings"), "settings")
        settings_btn.clicked.connect(lambda: self._go(5))
        sb_layout.addWidget(settings_btn)
        self._nav.append(settings_btn)

        return sidebar

    def _build_right_column(self) -> QWidget:
        """Build the main content column.

        Returns:
            Widget containing header, pages stack, and status bar.
        """
        right_col = QWidget()
        right_col.setObjectName("RightCol")
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        header = self._build_header()
        right_layout.addWidget(header)

        self._pages = QStackedWidget()
        self._pages.setObjectName("Content")
        self._add_pages()
        right_layout.addWidget(self._pages, 1)

        self._status = self.statusBar()
        if self._status:
            self._status.setObjectName("StatusBar")
            self._status.showMessage(tr("ready", "Ready"), 3000)

        return right_col

    def _build_header(self) -> QWidget:
        """Build the window header bar.

        Returns:
            Header widget with logo, title, and window controls.
        """
        header = QFrame()
        header.setObjectName("Header")
        header.setFixedHeight(42)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 0, 0)
        header_layout.setSpacing(0)

        self._logo_label = QLabel()
        logo_icon = ASSETS_DIR / "logo.ico"
        if logo_icon.exists():
            self._logo_label.setPixmap(QIcon(str(logo_icon)).pixmap(28, 28))
        else:
            logo_png = ASSETS_DIR / "logo.png"
            if logo_png.exists():
                self._logo_label.setPixmap(QIcon(str(logo_png)).pixmap(28, 28))
        self._logo_label.setFixedSize(36, 42)
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self._logo_label)

        self._title_label = QLabel(f"S.O.K - {tr('videos', 'Videos')}")
        self._title_label.setObjectName("AppTitle")
        header_layout.addWidget(self._title_label)

        self._drag_area = QWidget()
        self._drag_area.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._drag_area.setStyleSheet("background: transparent;")
        header_layout.addWidget(self._drag_area)

        min_btn = WindowControlButton("minimize")
        min_btn.clicked.connect(self.showMinimized)
        header_layout.addWidget(min_btn)

        self._max_btn = WindowControlButton("square")
        self._max_btn.clicked.connect(self._toggle_maximize)
        header_layout.addWidget(self._max_btn)

        close_btn = WindowControlButton("cross", "#FF5555")
        close_btn.top_right_radius = 12
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)

        return header

    def _add_pages(self):
        """Add all application pages to the stack widget.

        Creates home, organize, and settings pages.
        """
        home_page = HomePage()
        home_page.navigate.connect(self._go)
        self._pages.addWidget(home_page)

        self._pages.addWidget(OrganizePage("video"))
        self._pages.addWidget(OrganizePage("music"))
        self._pages.addWidget(OrganizePage("book"))
        self._pages.addWidget(OrganizePage("game"))

        settings_page = SettingsPage(self._toggle_theme)
        settings_page.language_changed.connect(self._on_language_changed)
        self._pages.addWidget(settings_page)

    def _on_language_changed(self, lang_code):
        """Handle language change from settings.

        Reloads translations and updates all UI text.

        Args:
            lang_code: New language code.
        """
        reload_language()
        self.retranslateUi()

        for i in range(self._pages.count()):
            page = self._pages.widget(i)
            if hasattr(page, "retranslateUi"):
                page.retranslateUi()  # type: ignore[union-attr]

    def retranslateUi(self):
        """Update all translatable text in the main window.

        Called after language changes to refresh UI strings.
        """
        self.lbl_library.setText(tr("library", "Library"))
        self.lbl_general.setText(tr("general", "General"))
        titles = self._nav_titles()

        for i, btn in enumerate(self._nav):
            if i < len(titles):
                btn.setText(titles[i])

        self._update_title_by_index(self._pages.currentIndex())

    def nativeEvent(self, eventType, message):
        """Handle native Windows events for frameless window resize.

        Processes WM_NCHITTEST messages to enable window resizing
        from edges and corners.

        Args:
            eventType: Type of native event.
            message: Native message pointer.

        Returns:
            Tuple of (handled, result) or parent result.
        """
        if eventType == b"windows_generic_MSG":
            msg = MSG.from_address(message.__int__())

            if msg.message == 0x0084:  # WM_NCHITTEST
                x = msg.lParam & 0xFFFF
                y = msg.lParam >> 16

                hit = hit_test_resize(x, y, self.frameGeometry())
                if hit is not None:
                    return True, hit
        return super().nativeEvent(eventType, message)

    def _toggle_maximize(self):
        """Toggle between maximized and normal window states.

        Animates the transition smoothly.
        """
        screen = self.screen().availableGeometry()
        start_rect = self.geometry()

        if self.isMaximized():
            end_rect = (
                self._restore_rect if self._restore_rect else self.normalGeometry()
            )

            self._anim_geo = QPropertyAnimation(self, b"geometry")
            self._anim_geo.setDuration(250)
            self._anim_geo.setStartValue(start_rect)
            self._anim_geo.setEndValue(end_rect)
            self._anim_geo.setEasingCurve(QEasingCurve.Type.OutCubic)

            def on_restore_finished():
                """Handle animation completion for window restore."""
                self.showNormal()
                self._max_btn._icon_name = "square"
                self._max_btn.update()

            self._anim_geo.finished.connect(on_restore_finished)
            self._anim_geo.start()

        else:
            self._restore_rect = self.geometry()
            end_rect = screen

            self._anim_geo = QPropertyAnimation(self, b"geometry")
            self._anim_geo.setDuration(250)
            self._anim_geo.setStartValue(start_rect)
            self._anim_geo.setEndValue(end_rect)
            self._anim_geo.setEasingCurve(QEasingCurve.Type.OutCubic)

            def on_max_finished():
                """Handle animation completion for window maximize."""
                self.showMaximized()
                self._max_btn._icon_name = "restore"
                self._max_btn.update()

            self._anim_geo.finished.connect(on_max_finished)
            self._anim_geo.start()

    def mouseDoubleClickEvent(self, event):
        """Handle double-click to toggle maximize.

        Args:
            event: Mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < 42:
                self._toggle_maximize()

    def mousePressEvent(self, event):
        """Handle mouse press for window dragging.

        Args:
            event: Mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < 42:
                if not self.isMaximized():
                    self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging.

        Args:
            event: Mouse event.
        """
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """Handle mouse release to end dragging.

        Args:
            event: Mouse event.
        """
        self._drag_pos = None

    def closeEvent(self, event):
        """Handle window close.

        Stops all page workers before closing.

        Args:
            event: Close event.
        """
        for page in self._iter_pages():
            if hasattr(page, "stop_workers"):
                page.stop_workers()
        event.accept()

    def _iter_pages(self):
        """Iterate over all pages in the stack.

        Yields:
            Each page widget.
        """
        for i in range(self._pages.count()):
            yield self._pages.widget(i)

    def _go(self, idx: int):
        """Navigate to a page by index.

        Args:
            idx: Page index to navigate to.
        """
        self._pages.setCurrentIndex(idx)
        self._update_title_by_index(idx)

        for i, btn in enumerate(self._nav):
            btn.setChecked(i == idx)

        if idx == 0:
            page = self._pages.widget(0)
            if hasattr(page, "refresh"):
                page.refresh()  # type: ignore[union-attr]

    def _nav_titles(self):
        """Get translated navigation button titles.

        Returns:
            List of translated title strings for sidebar buttons.
        """
        return [
            tr("home", "Home"),
            tr("videos", "Videos"),
            tr("music", "Music"),
            tr("books", "Books"),
            tr("games", "Games"),
            tr("settings", "Settings"),
        ]

    def _update_title_by_index(self, idx: int):
        """Update window title based on current page index.

        Args:
            idx: Current page index.
        """
        titles = self._nav_titles()
        if 0 <= idx < len(titles):
            self._title_label.setText(f"S.O.K - {titles[idx]}")

    def _toggle_sidebar(self):
        """Toggle sidebar between expanded and collapsed states.

        Animates the width transition and fades labels in/out.
        """
        if hasattr(self, "_sidebar_anim") and self._sidebar_anim:
            self._sidebar_anim.stop()

        self._sidebar_anim = QVariantAnimation(self)
        self._sidebar_anim.setDuration(250)
        self._sidebar_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        if self._sidebar_expanded:
            self._sidebar_anim.setStartValue(1.0)
            self._sidebar_anim.setEndValue(0.0)
            self._sidebar_expanded = False
        else:
            self._sidebar_anim.setStartValue(0.0)
            self._sidebar_anim.setEndValue(1.0)
            self._sidebar_expanded = True

        def on_value_changed(value):
            """Handle sidebar animation progress update.

            Args:
                value: Animation progress value (0.0 to 1.0).
            """
            width = int(72 + 148 * value)
            self._sidebar.setFixedWidth(width)

            for btn in self._nav:
                btn.set_progress(value)
            self._menu_btn.set_progress(value)

            for effect in self._sidebar_labels:
                effect.setOpacity(value)

        self._sidebar_anim.valueChanged.connect(on_value_changed)
        self._sidebar_anim.start()

    def _toggle_theme(self, dark: bool):
        """Switch between light and dark themes.

        Updates theme state, saves preference, and reapplies styles.

        Args:
            dark: True for dark theme, False for light.
        """
        self.dark = dark
        self._theme_name = "dark" if dark else "orange"
        self.c = Theme.DARK if dark else Theme.LIGHT

        if hasattr(self, "_config"):
            self._config.set("theme", self._theme_name)

        self._style()
        self.update()

    def _style(self):
        """Apply current theme stylesheet to the window.

        Generates and applies CSS based on current color theme.
        """
        c = self.c
        font = Theme.FONT

        self.setStyleSheet(
            f"""
            * {{
                font-family: '{font}';
                outline: none;
            }}

            QMainWindow, #Central {{
                background: transparent;
            }}

            /* Sidebar */
            #Sidebar {{
                background: {c["card"]};
                border-right: 1px solid {c["separator"]};
                border-top-left-radius: 12px;
                border-bottom-left-radius: 12px;
            }}

            #SidebarSection {{
                font-size: 11px;
                font-weight: 600;
                color: {c["secondary"]};
                padding: 16px 20px 6px 20px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}

            /* Right Column (Background + Radius) */
            #RightCol {{
                background: {c["bg"]};
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
            }}

            /* Header */
            #Header {{
                background: transparent;
                /* Optional bottom border */
                /* border-bottom: 1px solid {c["separator"]}; */
            }}

            #AppTitle {{
                font-size: 13px;
                font-weight: 600;
                color: {c["text"]};
                padding-left: 4px;
            }}

            /* Content Area (Transparent to show RightCol background) */
            #Content {{
                background: transparent;
            }}

            #Page {{
                background: transparent;
                border: none;
            }}

            #PageContent {{
                background: transparent;
            }}

            #PageTitle {{
                font-size: 28px;
                font-weight: 700;
                color: {c["text"]};
                margin-bottom: 10px;
            }}

            #SectionLabel, #CategoryLabel {{
                font-size: 11px;
                font-weight: 600;
                color: {c["secondary"]};
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-top: 10px;
                margin-bottom: 4px;
            }}

            #EmptyState {{
                color: {c["secondary"]};
                font-size: 13px;
            }}

            /* Common Widgets Stylesheet overrides for Card/Input */

            #Card {{
                background: {c.get("card_bg", c["card"])};
                border: 1px solid {c["separator"]};
                border-radius: {Theme.R}px;
            }}

            #Separator {{
                background: {c["separator"]};
                margin-left: 12px;
            }}

            /* Inputs */
            #SearchBar, #SettingsInput, #SettingsFormatInput {{
                background: {c.get("input_bg", c["card"])};
                border: 1px solid {c["separator"]};
                border-radius: 8px;
                padding: 4px 12px;
                color: {c["text"]};
                font-size: 13px;
            }}

            #SearchBar:focus, #SettingsInput:focus {{
                border-color: {c["accent"]};
            }}

            /* Combos */
            QComboBox {{
                background: {c.get("input_bg", c["card"])};
                border: 1px solid {c["separator"]};
                border-radius: 8px;
                padding: 4px 12px;
                color: {c["text"]};
            }}

            QComboBox:hover {{
                border-color: {c["accent"]};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}

            QComboBox QAbstractItemView {{
                background: {c.get("dropdown_bg", c["card"])};
                border: 1px solid {c["separator"]};
                border-radius: 12px;
                padding: 4px;
                outline: none;

                /* Force palette colors for Fusion style */
                selection-background-color: {c["accent"]};
                selection-color: {c["accent_text"]};
            }}

            QComboBox QAbstractItemView::item {{
                min-height: 32px;
                padding-left: 10px;
                border-radius: 6px;
                margin: 2px 0;
                color: {c["text"]};
            }}

            QComboBox QAbstractItemView::item:selected,
            QComboBox QAbstractItemView::item:hover {{
                background: {c["accent"]};
                color: {c["accent_text"]};
            }}

            /* Buttons */
            #ActionBtn {{
                background: {c["accent"]};
                border-radius: 16px;
                color: {c["accent_text"]};
                font-weight: 600;
                font-size: 13px;
                padding: 0 16px;
                border: none;
            }}

            #ActionBtn:hover {{
                background: {c["accent"]};
                opacity: 0.9;
            }}

            #ActionBtn:pressed {{
                background: {c["accent"]};
                margin-top: 1px;
                margin-bottom: -1px;
            }}

            #ActionBtn:disabled {{
                background: {c["separator"]};
                color: {c["secondary"]};
            }}

            #SmallBtn {{
                background: {c["accent"]};
                border-radius: 6px;
                color: {c["accent_text"]};
                font-weight: 600;
            }}

            #SmallBtn:hover {{
                background: {c["accent"]};
                opacity: 0.9;
            }}

            #SmallBtn:pressed {{
                background: {c["accent"]};
            }}

            #DestructiveBtn {{
                background: {c.get("red", "#FF5555")};
                border-radius: 16px;
                color: white;
                font-weight: 600;
            }}

            #DestructiveBtn:hover {{
                background: #FF6B6B;
            }}

            #DestructiveBtn:pressed {{
                background: #EE4444;
                margin-top: 1px;
                margin-bottom: -1px;
            }}

            /* ScrollBar */
            QScrollBar:vertical {{
                background: transparent;
                width: 14px;
                margin: 0;
            }}

            QScrollBar::handle:vertical {{
                background: {c.get("tertiary", "rgba(255,255,255,0.3)")};
                border-radius: 4px;
                min-height: 40px;
                margin: 2px 3px; /* Handle width = 14 - 6 = 8px. Radius 4px makes it fully round */
            }}

            QScrollBar::handle:vertical:hover {{
                background: {c.get("secondary", "rgba(255,255,255,0.5)")};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
                background: none;
            }}

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """
        )

        self.update()
        for w in self.findChildren(QWidget):
            try:
                w.update()
            except TypeError:
                pass


def main():
    """Application entry point.

    Creates QApplication, applies Fusion style, and shows main window.
    """
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
