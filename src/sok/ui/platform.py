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
from PySide6.QtGui import QColorSpace, QGuiApplication, QSurfaceFormat
from PySide6.QtWidgets import QApplication, QWidget

IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")
IS_WINDOWS = sys.platform == "win32"

# DwmSetWindowAttribute: DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND.
_DWM_CORNER_PREFERENCE = 33
_DWM_ROUND = 2

# Height of the macOS title bar the content is drawn under.
MACOS_TITLEBAR_HEIGHT = 28

# Value of the "theme" setting that follows the system appearance.
SYSTEM_THEME = "system"


def system_prefers_dark() -> bool:
    """Return True if the system appearance is dark."""
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def is_dark_theme(theme: str) -> bool:
    """Return True if the "theme" setting resolves to the dark palette.

    Args:
        theme: Setting value: "dark", "light" or "system" ("orange", the
            dropped orange theme, reads as "light").
    """
    if theme == SYSTEM_THEME:
        return system_prefers_dark()
    return theme == "dark"


def round_native_corners(window: QWidget) -> bool:
    """Ask Windows 11 to round the corners of a frameless window.

    The window is then opaque: a see-through window, which drew its own
    rounded corners, made Windows compose the whole window again at each
    frame of an animation, and the transitions stuttered. Windows 10 knows
    no rounded corners: the window keeps square ones there.

    Returns:
        True if Windows rounds them.
    """
    if not IS_WINDOWS:
        return False
    try:
        import ctypes

        preference = ctypes.c_int(_DWM_ROUND)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(  # type: ignore[attr-defined]
            ctypes.c_void_p(int(window.winId())),
            _DWM_CORNER_PREFERENCE,
            ctypes.byref(preference),
            ctypes.sizeof(preference),
        )
    except (OSError, AttributeError):
        return False
    return result == 0


def use_srgb_windows() -> None:
    """Tell macOS that the windows are drawn in sRGB (call before the first one).

    Without a color space, Qt hands its pixels to macOS untagged, and macOS
    shows them in the color space of the screen: on a wide-gamut external
    screen the coral of S.O.K turned a vivid red, while the other apps,
    tagged sRGB, kept their colors. The colors of the theme are sRGB values.
    """
    if not IS_MACOS:
        return
    surface = QSurfaceFormat.defaultFormat()
    surface.setColorSpace(QColorSpace(QColorSpace.NamedColorSpace.SRgb))
    QSurfaceFormat.setDefaultFormat(surface)


def apply_color_scheme(theme: str) -> None:
    """Make the native macOS chrome match the "theme" setting.

    The title bar, traffic lights and native dialogs follow the application
    appearance. A forced theme overrides it; "system" removes the override,
    so system_prefers_dark() reports the real system appearance again.

    Args:
        theme: Setting value: "dark", "light" or "system" ("orange", the
            dropped orange theme, reads as "light").
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
