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
"""Sizes that follow the size of the window.

The pages call these from their resizeEvent: the right column (scene,
preview, summary) takes about a third of the page, the big titles get
smaller in a narrow window, and the content of the window stops growing past
MAX_CONTENT_WIDTH, centered (see CenteredColumn).
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget

from sok.ui.theme import ui_font

# Widest the navigation and the pages get; past it they are centered.
MAX_CONTENT_WIDTH = 1760

# The right column: about 36% of the page, from 320 to 520px (the mockups
# give it 420 to 520).
SIDE_SHARE = 0.36
SIDE_MIN, SIDE_MAX = 320, 520

# Height under which the decorations of a screen (the empty places of the
# empty screen, the covers of the summary) leave room for the text.
LOW_HEIGHT = 620


def side_width(page_width: int) -> int:
    """Width of the right column of a page this wide."""
    return max(SIDE_MIN, min(SIDE_MAX, round(page_width * SIDE_SHARE)))


def display_px(page_width: int) -> int:
    """Size of the big title of a page this wide: 52px, down to 40px."""
    if page_width >= 1180:
        return 52
    if page_width >= 980:
        return 46
    return 40


def display_font(page_width: int) -> QFont:
    """The big title font (weight 650, tracking -0.04em) for a page width."""
    px = display_px(page_width)
    font = ui_font(px, 650)
    font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, -0.04 * px)
    return font


def fit_display(labels: list[QLabel], page_width: int) -> None:
    """Give these big titles the size of the page width."""
    px = display_px(page_width)
    for label in labels:
        if label.font().pixelSize() != px:
            label.setFont(display_font(page_width))


class CenteredColumn(QWidget):
    """Holds one widget, as wide as the window up to MAX_CONTENT_WIDTH, then
    centered with empty margins on both sides."""

    def __init__(self, child: QWidget, parent=None):
        super().__init__(parent)
        self._child = child
        child.setParent(self)

    def resizeEvent(self, e):  # noqa: N802 - Qt API
        super().resizeEvent(e)
        width = min(self.width(), MAX_CONTENT_WIDTH)
        self._child.setGeometry((self.width() - width) // 2, 0, width, self.height())

    def sizeHint(self):  # noqa: N802 - Qt API
        return self._child.sizeHint()

    def minimumSizeHint(self):  # noqa: N802 - Qt API
        return self._child.minimumSizeHint()
