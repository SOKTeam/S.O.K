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

import logging
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPixmap
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget
from PySide6.QtSvg import QSvgRenderer
import re

from sok.config.config_manager import resources_dir
from sok.ui import tokens
from sok.ui.platform import IS_LINUX, IS_MACOS, system_accent_color

logger = logging.getLogger(__name__)

ASSETS_DIR = resources_dir() / "assets"
FONTS_DIR = resources_dir() / "fonts"

# Window icon: the rounded orange square on Linux, where the black cube
# disappears on dark panels.
APP_ICON = ASSETS_DIR / ("logo_linux.png" if IS_LINUX else "logo.ico")


def load_bundled_fonts() -> None:
    """Register the bundled Geist and Geist Mono fonts (see Theme.FONT).

    The art direction uses them on every system, so they ship with the app
    (variable fonts, SIL Open Font License). Needs a QGuiApplication.
    """
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        if QFontDatabase.addApplicationFont(str(path)) < 0:
            logger.warning("Could not load font %s", path.name)


def _legacy_palette(t: dict[str, str]) -> dict[str, str]:
    """Return a palette with the color names the widgets use, from tokens.

    The widgets still read names such as "text" or "card"; each one points to
    a token of the art direction. The tokens themselves are included too, for
    the widgets drawn with them.

    Args:
        t: Color tokens of one theme (see sok.ui.tokens).
    """
    return {
        **t,
        "bg": t["bg"],
        "card": t["surface"],
        "card_bg": t["surface"],
        "sidebar": t["surface"],
        "sidebar_selection": t["surface-raised"],
        "dropdown_bg": t["surface-raised"],
        "input_bg": t["surface-raised"],
        "hover": t["surface-raised"],
        "text": t["ink"],
        "secondary": t["ink-muted"],
        "tertiary": t["key"],
        "icon_secondary": t["ink-muted"],
        "separator": t["line"],
        "accent": t["accent"],
        "accent_text": t["on-accent"],
        "red": t["danger"],
        # No success color: "ok" and "renamed" use the normal text color,
        # next to a word that says it.
        "tone_ok": t["ink"],
        "tone_warn": t["caution"],
        "tone_error": t["danger"],
        "tone_info": t["ink-muted"],
        "tone_disabled": t["ink-faint"],
        "tone_file": t["ink-muted"],
        "tone_pending": t["ink-faint"],
        "tone_renamed": t["ink"],
        "tone_ambiguous": t["caution"],
        "tone_missing": t["danger"],
    }


class Theme:
    """Design tokens and color palettes for S.O.K UI.

    The colors come from the SOKTeam art direction (sok.ui.tokens, generated
    by scripts/make_theme_tokens.py), the same on every system.

    Attributes:
        FONT: UI font name (the bundled Geist).
        MONO: Font name for data: paths, file names, years, figures,
            shortcuts (the bundled Geist Mono).
        LIGHT: Light theme color dictionary.
        DARK: Dark theme color dictionary, the one screens are judged on.
    """

    FONT = "Geist"
    MONO = "Geist Mono"

    LIGHT = {**_legacy_palette(tokens.LIGHT), "font": FONT}

    DARK = {**_legacy_palette(tokens.DARK), "font": FONT}

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
        accent = system_accent_color()
        c["accent"] = c["accent-text"] = accent
        # The near-black text of the coral is not readable on every system
        # color (blue, purple, graphite): keep white there.
        c["accent_text"] = c["on-accent"] = "#FFFFFF"
    return c


def ui_font(
    px: int, weight: int = 400, mono: bool = False, tabular: bool = False
) -> QFont:
    """Return a font of the art direction at an exact size and weight.

    Stylesheets round a weight to the nearest named one (650 becomes 600);
    this sets the weight axis of the variable font, so any weight works.

    Args:
        px: Size in pixels.
        weight: Weight, 100 to 900 (the titles use 650).
        mono: Geist Mono instead of Geist.
        tabular: Figures of equal width, for columns of numbers (Geist Mono
            always has them).
    """
    font = QFont(Theme.MONO if mono else Theme.FONT)
    font.setPixelSize(px)
    font.setWeight(QFont.Weight(min(max(weight, 100), 900)))
    font.setVariableAxis(QFont.Tag("wght"), float(weight))
    if tabular:
        font.setFeature(QFont.Tag("tnum"), 1)
    return font


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
