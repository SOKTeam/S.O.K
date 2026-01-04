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
Design Tokens and Theme Utilities for S.O.K
"""

import sys
import os
from pathlib import Path
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtSvg import QSvgRenderer
import re

# 1. Detect if running as executable or in script mode
if "__compiled__" in globals():
    # In a Nuitka build, assets are next to the executable
    # or in the .dist folder (if standalone)
    # We assume the 'resources' folder is distributed with the app
    ROOT_DIR = Path(sys.executable).parent
    ASSETS_DIR = ROOT_DIR / "resources" / "assets"
else:
    # Development mode:
    # src/sok/ui/theme.py -> parent -> src/sok/ui -> parent -> src/sok
    PACKAGE_ROOT = Path(__file__).resolve().parent.parent
    ASSETS_DIR = PACKAGE_ROOT / "resources" / "assets"


class Theme:
    """Design tokens and color palettes for S.O.K UI.

    Provides LIGHT and DARK color dictionaries plus platform-aware
    font selection.

    Attributes:
        FONT: System font name (SF Pro, Segoe UI, or Inter).
        LIGHT: Orange theme color dictionary.
        DARK: Dark theme color dictionary.
    """

    FONT = (
        "SF Pro Text"
        if sys.platform == "darwin"
        else ("Segoe UI Variable" if os.name == "nt" else "Inter")
    )

    LIGHT = {
        "bg": "#FB6048",
        "card": "#FB6048",
        "card_bg": "rgba(255, 255, 255, 0.15)",
        "dropdown_bg": "#DD513F",
        "text": "#FFFFFF",
        "secondary": "rgba(255, 255, 255, 0.9)",
        "tertiary": "rgba(255, 255, 255, 0.6)",
        "accent": "#FFFFFF",
        "accent_text": "#FB6048",
        "green": "#50FA7B",
        "red": "#FF5555",
        "separator": "rgba(255, 255, 255, 0.3)",
        "hover": "rgba(255, 255, 255, 0.3)",
        "input_bg": "rgba(255, 255, 255, 0.25)",
        "icon_secondary": "#FFFFFF",
        "font": FONT,
    }

    DARK = {
        "bg": "#121212",
        "card": "#1E1E1E",
        "card_bg": "#1E1E1E",
        "dropdown_bg": "#2C2C2E",
        "text": "#FFFFFF",
        "secondary": "#B3B3B3",
        "tertiary": "#404040",
        "accent": "#FB6048",
        "accent_text": "#FFFFFF",
        "green": "#30D158",
        "red": "#FF453A",
        "separator": "#333333",
        "hover": "rgba(255, 255, 255, 0.1)",
        "input_bg": "#2C2C2E",
        "icon_secondary": "#B3B3B3",
        "font": FONT,
    }

    R = 10


def svg_icon(name: str, color: str, size: int = 22) -> QPixmap:
    """Load SVG icon with custom color.

    Args:
        name: Icon name (without .svg extension).
        color: Color to apply to stroke and fill.
        size: Icon size in pixels.

    Returns:
        QPixmap with the colored icon.
    """
    path = ASSETS_DIR / f"{name}.svg"
    if not path.exists():
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        return pm

    with open(path, "r", encoding="utf-8") as f:
        svg = f.read()

    svg = re.sub(
        r'stroke=(["\'])(?!none\1).*?\1',
        f"stroke=\\1{color}\\1",
        svg,
        flags=re.IGNORECASE,
    )
    svg = re.sub(
        r'fill=(["\'])(?!none\1).*?\1', f"fill=\\1{color}\\1", svg, flags=re.IGNORECASE
    )

    renderer = QSvgRenderer(svg.encode("utf-8"))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    renderer.render(p)
    p.end()
    return pm


def card_shadow() -> QGraphicsDropShadowEffect:
    """Create subtle shadow effect for cards.

    Returns:
        Configured drop shadow effect.
    """
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(20)
    shadow.setOffset(0, 2)
    shadow.setColor(QColor(0, 0, 0, 15))
    return shadow
