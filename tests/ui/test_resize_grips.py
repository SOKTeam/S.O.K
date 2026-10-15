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
from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QWidget

from sok.ui.controllers.window_chrome import ResizeGrips

Edge = Qt.Edge


def grips_by_edges(window):
    return {grip.edges: grip for grip in window.findChildren(QWidget)}


def test_grips_cover_edges_and_corners(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    grips = ResizeGrips(window, border_width=6)
    grips.update_geometry(400, 300)
    by_edges = grips_by_edges(window)

    assert by_edges[Edge.LeftEdge].geometry() == QRect(0, 6, 6, 288)
    assert by_edges[Edge.RightEdge].geometry() == QRect(394, 6, 6, 288)
    assert by_edges[Edge.TopEdge].geometry() == QRect(6, 0, 388, 6)
    assert by_edges[Edge.BottomEdge].geometry() == QRect(6, 294, 388, 6)
    assert by_edges[Edge.TopEdge | Edge.LeftEdge].geometry() == QRect(0, 0, 6, 6)
    corner = by_edges[Edge.BottomEdge | Edge.RightEdge]
    assert corner.geometry() == QRect(394, 294, 6, 6)


def test_corner_grips_show_diagonal_cursors(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    ResizeGrips(window)
    by_edges = grips_by_edges(window)

    top_left = by_edges[Edge.TopEdge | Edge.LeftEdge].cursor().shape()
    top_right = by_edges[Edge.TopEdge | Edge.RightEdge].cursor().shape()
    assert top_left == Qt.CursorShape.SizeFDiagCursor
    assert top_right == Qt.CursorShape.SizeBDiagCursor


def test_hidden_while_maximized(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    window.show()
    grips = ResizeGrips(window)

    grips.set_visible(False)

    assert not any(g.isVisible() for g in window.findChildren(QWidget))
