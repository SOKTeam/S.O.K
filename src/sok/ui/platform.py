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
"""Platform-specific window behavior.

Windows and Linux use a frameless window with custom title bar buttons.
macOS keeps the native window (traffic lights, resize, full screen) and
extends the content under its title bar.
"""

import ctypes
import sys
import warnings

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QWidget

IS_MACOS = sys.platform == "darwin"

# Height of the macOS title bar the content is drawn under.
MACOS_TITLEBAR_HEIGHT = 28

# Value of the "theme" setting that follows the system appearance.
SYSTEM_THEME = "system"


def system_prefers_dark() -> bool:
    """Return True if the system appearance is dark."""
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def system_accent_color() -> str:
    """Return the accent color chosen in the system settings, as "#RRGGBB"."""
    return QGuiApplication.palette().color(QPalette.ColorRole.Accent).name()


def is_dark_theme(theme: str) -> bool:
    """Return True if the "theme" setting resolves to the dark palette.

    Args:
        theme: Setting value: "dark", "light", "orange" or "system".
    """
    if theme == SYSTEM_THEME:
        return system_prefers_dark()
    return theme == "dark"


def apply_color_scheme(theme: str) -> None:
    """Make the native macOS chrome match the "theme" setting.

    The title bar, traffic lights and native dialogs follow the application
    appearance. A forced theme overrides it; "system" removes the override,
    so system_prefers_dark() reports the real system appearance again.

    Args:
        theme: Setting value: "dark", "light", "orange" or "system".
    """
    if not IS_MACOS:
        return
    if theme == SYSTEM_THEME:
        scheme = Qt.ColorScheme.Unknown
    elif theme == "dark":
        scheme = Qt.ColorScheme.Dark
    else:
        scheme = Qt.ColorScheme.Light
    QGuiApplication.styleHints().setColorScheme(scheme)


def use_native_title_bar(window: QWidget) -> None:
    """Keep the native macOS window and draw the content under its title bar.

    Args:
        window: Top-level window to configure before it is shown.
    """
    with warnings.catch_warnings():
        # PySide6 flags ExpandedClientAreaHint as deprecated because it shares
        # its value with the deprecated MaximizeUsingFullscreenGeometryHint.
        warnings.simplefilter("ignore", DeprecationWarning)
        window.setWindowFlag(Qt.WindowType.ExpandedClientAreaHint, True)
    window.setWindowFlag(Qt.WindowType.NoTitleBarBackgroundHint, True)
    # Layouts handle the title bar area themselves (see MACOS_TITLEBAR_HEIGHT).
    window.setAttribute(Qt.WidgetAttribute.WA_ContentsMarginsRespectsSafeArea, False)


# NSWindowTitleVisibility.NSWindowTitleHidden
_NS_WINDOW_TITLE_HIDDEN = 1


def hide_native_title(window: QWidget) -> None:
    """Hide the title text macOS centers on the whole window (macOS only).

    The window keeps its title (Window menu, Mission Control); the app
    draws it centered on the content instead. Uses the Objective-C runtime
    through ctypes, so no extra dependency is needed.

    Args:
        window: Shown top-level window.
    """
    # winId() is an NSView only on the native platform (not "offscreen").
    if not IS_MACOS or QGuiApplication.platformName() != "cocoa":
        return
    objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    msg_send = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value
    if msg_send is None:
        return
    # arm64 needs the exact prototype of each call (objc_msgSend is not
    # variadic there).
    get_object = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
        msg_send
    )
    set_long = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long)(
        msg_send
    )

    ns_view = int(window.winId())
    ns_window = get_object(ns_view, objc.sel_registerName(b"window"))
    if ns_window:
        set_long(
            ns_window,
            objc.sel_registerName(b"setTitleVisibility:"),
            _NS_WINDOW_TITLE_HIDDEN,
        )


def request_attention(widget: QWidget) -> None:
    """Bounce the Dock icon when a long task ends in the background (macOS).

    Args:
        widget: Widget whose window finished the task.
    """
    window = widget.window()
    if IS_MACOS and not window.isActiveWindow():
        QApplication.alert(window)
