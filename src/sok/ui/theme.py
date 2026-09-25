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
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget
from PySide6.QtSvg import QSvgRenderer
import re

from sok.config.config_manager import resources_dir
from sok.ui.platform import IS_MACOS, system_accent_color

ASSETS_DIR = resources_dir() / "assets"


class Theme:
    """Design tokens and color palettes for S.O.K UI.

    Provides LIGHT and DARK color dictionaries plus platform-aware
    font selection.

    Attributes:
        FONT: System font name (macOS system font, Segoe UI, or Inter).
        ORANGE: Orange theme color dictionary.
        MAC_LIGHT: macOS light theme: white and gray, orange accents.
        LIGHT: Light theme of the current platform.
        DARK: Dark theme color dictionary.
    """

    FONT = (
        # Name Qt gives the macOS system font (SF Pro): "SF Pro Text" is not
        # an installed family name, so Qt fell back to it with a warning.
        ".AppleSystemUIFont"
        if sys.platform == "darwin"
        else ("Segoe UI Variable" if os.name == "nt" else "Inter")
    )

    ORANGE = {
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
        "tone_ok": "#50FA7B",
        "tone_warn": "#FFB86C",
        "tone_error": "#FF6B6B",
        "tone_info": "rgba(255, 255, 255, 0.7)",
        "tone_disabled": "rgba(255, 255, 255, 0.4)",
        "tone_file": "#B3B3B3",
        "tone_pending": "#404040",
        "tone_renamed": "#30D158",
        "tone_ambiguous": "#FFB347",
        "tone_missing": "#FF453A",
        "font": FONT,
    }

    MAC_LIGHT = {
        "bg": "#FFFFFF",
        "card": "#F5F5F7",
        "sidebar": "#EDEDF0",
        "sidebar_selection": "rgba(0, 0, 0, 0.1)",
        "card_bg": "#F5F5F7",
        "dropdown_bg": "#FFFFFF",
        "text": "#1D1D1F",
        "secondary": "#6E6E73",
        "tertiary": "#C7C7CC",
        "accent": "#FB6048",
        "accent_text": "#FFFFFF",
        "green": "#248A3D",
        "red": "#D70015",
        "separator": "#E3E3E8",
        "hover": "rgba(0, 0, 0, 0.06)",
        "input_bg": "#FFFFFF",
        "icon_secondary": "#6E6E73",
        "tone_ok": "#248A3D",
        "tone_warn": "#B25000",
        "tone_error": "#D70015",
        "tone_info": "#6E6E73",
        "tone_disabled": "#AEAEB2",
        "tone_file": "#6E6E73",
        "tone_pending": "#AEAEB2",
        "tone_renamed": "#248A3D",
        "tone_ambiguous": "#B25000",
        "tone_missing": "#D70015",
        "font": FONT,
    }

    LIGHT = MAC_LIGHT if IS_MACOS else ORANGE

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
        "sidebar_selection": "rgba(255, 255, 255, 0.1)",
        "tone_ok": "#50FA7B",
        "tone_warn": "#FFB86C",
        "tone_error": "#FF6B6B",
        "tone_info": "rgba(255, 255, 255, 0.7)",
        "tone_disabled": "rgba(255, 255, 255, 0.4)",
        "tone_file": "#B3B3B3",
        "tone_pending": "#404040",
        "tone_renamed": "#30D158",
        "tone_ambiguous": "#FFB347",
        "tone_missing": "#FF453A",
        "font": FONT,
    }

    R = 10

    # Colored text, applied with set_tone(): "tone_ok" styles tone "ok".
    TONE_PREFIX = "tone_"


def palette(dark: bool, system_accent: bool = False) -> dict[str, str]:
    """Return the color palette to use.

    Args:
        dark: True for the dark theme.
        system_accent: Replace the orange accent with the system accent
            color (macOS setting).
    """
    c = dict(Theme.DARK if dark else Theme.LIGHT)
    if system_accent and IS_MACOS:
        c["accent"] = system_accent_color()
    return c


def tone_stylesheet(c: dict[str, str]) -> str:
    """Return the stylesheet rules coloring the widgets given a tone.

    Args:
        c: Color palette.
    """
    return "\n".join(
        f'*[tone="{key.removeprefix(Theme.TONE_PREFIX)}"] {{ color: {value}; }}'
        for key, value in c.items()
        if key.startswith(Theme.TONE_PREFIX)
    )


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


def set_tone(widget: QWidget, tone: str | None) -> None:
    """Color a widget's text with a palette tone.

    The main window stylesheet maps each "tone_<name>" palette entry to the
    widgets whose "tone" property is <name>, so the color follows the theme.

    Args:
        widget: Widget to color.
        tone: Tone name, such as "ok" or "error"; None for the default color.
    """
    widget.setProperty("tone", tone or "")
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


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
