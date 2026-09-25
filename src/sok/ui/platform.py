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

import sys
import warnings

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

IS_MACOS = sys.platform == "darwin"

# Height of the macOS title bar the content is drawn under.
MACOS_TITLEBAR_HEIGHT = 28


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
