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
Visuals of a media item: its dominant color and a stand-in when it has none.

The art direction never shows an empty grey rectangle for a missing poster:
the stand-in is a gradient of a color taken from the title, with the year and
the title written on it.
"""

import zlib

from typing import Collection, Optional, Sequence, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

from sok.ui.theme import ui_font


def dominant_color(image: QImage | QPixmap) -> QColor:
    """Return the average color of an image, computed on a reduced copy.

    Args:
        image: Poster, cover or any picture.
    """
    if isinstance(image, QPixmap):
        image = image.toImage()
    if image.isNull():
        return QColor(128, 128, 128)
    small = image.scaled(
        16,
        16,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    ).convertToFormat(QImage.Format.Format_RGB32)
    r = g = b = 0
    for y in range(16):
        for x in range(16):
            color = small.pixelColor(x, y)
            r += color.red()
            g += color.green()
            b += color.blue()
    return QColor(r // 256, g // 256, b // 256)


def standin_colors(title: str) -> tuple[QColor, QColor]:
    """Return the two colors of the stand-in gradient of a title.

    The hue comes from the title, so the same item always gets the same
    stand-in; the light top color fades to a near-black of the same hue.
    """
    hue = zlib.crc32(title.encode("utf-8")) % 360
    return QColor.fromHsl(hue, 90, 125), QColor.fromHsl(hue, 70, 22)


def standin_pixmap(
    title: str,
    year: str,
    width: int,
    height: int,
    ratio: float = 1.0,
    text: bool = True,
) -> QPixmap:
    """Draw the stand-in of a missing visual: gradient, year and title.

    Args:
        title: Title written at the bottom.
        year: Small capitals above the title ("" for none).
        width: Width in pixels.
        height: Height in pixels.
        ratio: Device pixel ratio of the screen.
        text: Write the year and the title (not when they are written under
            the visual, as in a grid of albums).
    """
    pixmap = QPixmap(int(width * ratio), int(height * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    top, bottom = standin_colors(title)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(0, 0, width * 0.35, height)
    gradient.setColorAt(0, top)
    gradient.setColorAt(1, bottom)
    p.fillRect(QRectF(0, 0, width, height), gradient)

    if text and width >= 80:
        pad = round(width * 0.08)
        size = max(12, round(width * 0.105))
        title_font = ui_font(size, 700)
        title_rect = QRectF(pad, 0, width - 2 * pad, height - pad)
        p.setFont(title_font)
        p.setPen(QColor(255, 255, 255))
        flags = (
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignBottom
            | Qt.TextFlag.TextWordWrap
        )
        bounds = p.boundingRect(title_rect, flags, title)
        p.drawText(title_rect, flags, title)
        if year:
            p.setFont(ui_font(max(8, round(size * 0.42)), 600))
            p.setPen(QColor(255, 255, 255, 190))
            p.drawText(
                QRectF(pad, bounds.top() - 18, width - 2 * pad, 14),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
                year.upper(),
            )
    p.end()
    return pixmap


def rounded(pixmap: QPixmap, width: int, height: int, radius: float) -> QPixmap:
    """Return the pixmap cropped to fill width x height, with rounded corners."""
    ratio = pixmap.devicePixelRatio() or 1.0
    out = QPixmap(int(width * ratio), int(height * ratio))
    out.setDevicePixelRatio(ratio)
    out.fill(Qt.GlobalColor.transparent)
    scaled = pixmap.scaled(
        int(width * ratio),
        int(height * ratio),
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(ratio)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, width, height), radius, radius)
    p.setClipPath(path)
    sw = scaled.width() / ratio
    sh = scaled.height() / ratio
    p.drawPixmap(
        QRectF((width - sw) / 2, (height - sh) / 2, sw, sh),
        scaled,
        QRectF(scaled.rect()),
    )
    p.end()
    return out


def draw_fan(
    p: QPainter,
    covers: Sequence[Tuple[Optional[QPixmap], str]],
    x: float,
    y: float,
    size: Tuple[int, int],
    step: float,
    radius: float,
    ratio: float,
    skip: Collection[int] = (),
) -> None:
    """Draw covers overlapping from left to right, the first on top; the
    covers at the indexes in skip are left out."""
    w, h = size
    for index in reversed(range(len(covers))):
        if index in skip:
            continue
        pixmap, title = covers[index]
        source = pixmap or standin_pixmap(title, "", w, h, ratio, text=False)
        p.drawPixmap(QPointF(x + index * step, y), rounded(source, w, h, radius))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 26), 1))
        p.drawRoundedRect(
            QRectF(x + index * step + 0.5, y + 0.5, w - 1, h - 1), radius, radius
        )
