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
Generate the macOS app icon (logo.icns) and the disk image background.

The S.O.K cube is drawn as vectors, so every size stays sharp. The icon
follows the macOS grid: a rounded-square body of 824 px in a 1024 px
canvas, with continuous corners and a soft shadow. Run on macOS:

    python scripts/make_macos_assets.py
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "src" / "sok" / "resources" / "assets"
MACOS_DIR = ROOT_DIR / "packaging" / "macos"

BRAND_LIGHT = QColor("#FF7C5F")
BRAND = QColor("#FB6048")
BRAND_DARK = QColor("#E8452F")

# Cube outline on a 1024 px grid, traced from logo.png.
CUBE_OUTLINE = [
    (255, 243),
    (512, 128),
    (884, 295),
    (884, 722),
    (512, 893),
    (140, 722),
    (140, 295),
    (512, 464),
    (884, 295),
]
CUBE_EDGE = [(512, 565), (512, 893)]
CUBE_STROKE = 42

# Disk image window, in points (the background also exists at 2x).
DMG_SIZE = (660, 420)
DMG_APP_POS = (180, 215)
DMG_APPLICATIONS_POS = (480, 215)


def icon_shape(rect: QRectF) -> QPainterPath:
    """Return the macOS icon body shape (corner radius of the Apple grid).

    Args:
        rect: Icon body rectangle.
    """
    radius = rect.width() * 185 / 824
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def draw_cube(p: QPainter, rect: QRectF, color: QColor, weight: float = 1.0) -> None:
    """Draw the S.O.K cube in the given square.

    Args:
        p: Active painter.
        rect: Square receiving the cube (the 1024 grid is scaled to it).
        color: Stroke color.
        weight: Stroke width factor, above 1 for small renderings.
    """
    scale = rect.width() / 1024

    def point(x: float, y: float) -> QPointF:
        return QPointF(rect.x() + x * scale, rect.y() + y * scale)

    pen = QPen(color, CUBE_STROKE * scale * weight)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for line in (CUBE_OUTLINE, CUBE_EDGE):
        path = QPainterPath(point(*line[0]))
        for x, y in line[1:]:
            path.lineTo(point(x, y))
        p.drawPath(path)


def render_icon(size: int) -> QImage:
    """Render the app icon at the given pixel size.

    Args:
        size: Width and height in pixels.
    """
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 1024, size / 1024)

    body = QRectF(100, 100, 824, 824)

    # Soft shadow under the body, as in the macOS icon template.
    for i in range(12, 0, -1):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 5))
        p.drawPath(icon_shape(body.adjusted(-i, -i + 10, i, i + 10)))

    gradient = QLinearGradient(body.topLeft(), body.bottomLeft())
    gradient.setColorAt(0, BRAND_LIGHT)
    gradient.setColorAt(1, BRAND_DARK)
    shape = icon_shape(body)
    p.fillPath(shape, gradient)

    # Light from the top, as on the system icons.
    glow = QRadialGradient(QPointF(512, 100), 700)
    glow.setColorAt(0, QColor(255, 255, 255, 60))
    glow.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillPath(shape, glow)

    draw_cube(p, QRectF(232, 232, 560, 560), QColor("white"), weight=1.35)
    p.end()
    return image


def make_icns(output: Path) -> None:
    """Write the .icns file with every size macOS uses.

    Args:
        output: Destination .icns path.
    """
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "logo.iconset"
        iconset.mkdir()
        for points in (16, 32, 128, 256, 512):
            render_icon(points).save(str(iconset / f"icon_{points}x{points}.png"))
            render_icon(points * 2).save(
                str(iconset / f"icon_{points}x{points}@2x.png")
            )
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(output)], check=True
        )


def render_dmg_background(scale: int) -> QImage:
    """Render the disk image window background.

    Args:
        scale: 1 for standard displays, 2 for Retina.
    """
    width, height = DMG_SIZE
    image = QImage(width * scale, height * scale, QImage.Format.Format_ARGB32)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(scale, scale)

    gradient = QLinearGradient(0, 0, 0, height)
    gradient.setColorAt(0, QColor("#FFFFFF"))
    gradient.setColorAt(1, QColor("#FFF1EC"))
    p.fillRect(QRectF(0, 0, width, height), gradient)

    # Brand band at the top.
    band = QLinearGradient(0, 0, width, 0)
    band.setColorAt(0, BRAND_LIGHT)
    band.setColorAt(1, BRAND_DARK)
    p.fillRect(QRectF(0, 0, width, 6), band)

    p.setPen(QColor("#1D1D1F"))
    title = QFont(".AppleSystemUIFont", 26)
    title.setWeight(QFont.Weight.Bold)
    p.setFont(title)
    p.drawText(QRectF(0, 36, width, 40), Qt.AlignmentFlag.AlignCenter, "S.O.K")
    p.setPen(QColor("#6E6E73"))
    p.setFont(QFont(".AppleSystemUIFont", 13))
    p.drawText(
        QRectF(0, 74, width, 24),
        Qt.AlignmentFlag.AlignCenter,
        "Storage Organisation Kit",
    )

    # Arrow from the app to the Applications folder.
    x1, y = DMG_APP_POS[0] + 80, DMG_APP_POS[1]
    x2 = DMG_APPLICATIONS_POS[0] - 80
    pen = QPen(BRAND, 4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setDashPattern([0.1, 3])
    p.setPen(pen)
    p.drawLine(QPointF(x1, y), QPointF(x2 - 14, y))
    pen.setStyle(Qt.PenStyle.SolidLine)
    p.setPen(pen)
    head = QPainterPath(QPointF(x2 - 14, y - 12))
    head.lineTo(QPointF(x2, y))
    head.lineTo(QPointF(x2 - 14, y + 12))
    p.drawPath(head)
    p.end()
    return image


def make_dmg_background(output: Path) -> None:
    """Write the background as a two-resolution TIFF, sharp on Retina.

    Args:
        output: Destination .tiff path.
    """
    with tempfile.TemporaryDirectory() as tmp:
        one_x = Path(tmp) / "background.png"
        two_x = Path(tmp) / "background@2x.png"
        render_dmg_background(1).save(str(one_x))
        render_dmg_background(2).save(str(two_x))
        subprocess.run(
            ["tiffutil", "-cathidpicheck", str(one_x), str(two_x), "-out", str(output)],
            check=True,
        )


def main() -> None:
    """Generate logo.icns and the disk image background."""
    if sys.platform != "darwin" or not shutil.which("iconutil"):
        sys.exit("This script needs macOS (iconutil, tiffutil).")
    app = QGuiApplication(sys.argv)  # noqa: F841 - needed for fonts
    MACOS_DIR.mkdir(parents=True, exist_ok=True)
    make_icns(ASSETS_DIR / "logo.icns")
    render_icon(1024).save(str(MACOS_DIR / "icon_1024.png"))
    make_dmg_background(MACOS_DIR / "dmg_background.tiff")
    print(f"Wrote {ASSETS_DIR / 'logo.icns'} and {MACOS_DIR}")


if __name__ == "__main__":
    main()
