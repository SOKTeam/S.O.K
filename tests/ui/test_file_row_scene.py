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
from PySide6.QtGui import QColor, QImage, QPixmap

from sok.ui.components.file_row import FileRow, RowData
from sok.ui.components.media_visual import dominant_color, standin_colors
from sok.ui.components.scene import Scene, SceneItem
from sok.ui.theme import Theme


def test_dominant_color_is_the_average():
    image = QImage(10, 10, QImage.Format.Format_RGB32)
    image.fill(QColor(200, 100, 50))

    assert dominant_color(image) == QColor(200, 100, 50)


def test_standin_colors_depend_only_on_the_title():
    assert standin_colors("Dune") == standin_colors("Dune")
    assert standin_colors("Dune") != standin_colors("Past Lives")


def test_selected_row_gets_the_raised_background(qtbot):
    row = FileRow(RowData("Dune", "dune.mkv", "2021"))
    qtbot.addWidget(row)
    row.resize(600, row.HEIGHT)
    raised = QColor(Theme.DARK["surface-raised"])

    row.set_selected(True)

    assert row.grab().toImage().pixelColor(300, 3) == raised


def test_gauge_fills_the_confidence(qtbot):
    row = FileRow(RowData("Dune", confidence=2))
    qtbot.addWidget(row)
    row.resize(600, row.HEIGHT)
    image = row.grab().toImage()
    ratio = image.devicePixelRatio()
    # The five notches end 14px from the right edge, 6px apart.
    first_x = 600 - 14 - 27 + 1
    notches = [
        image.pixelColor(int((first_x + i * 6) * ratio), int(row.HEIGHT // 2 * ratio))
        for i in range(5)
    ]

    accent = QColor(Theme.DARK["accent"])
    assert notches[:2] == [accent, accent]
    assert accent not in notches[2:]


def test_scene_hides_what_the_item_lacks(qtbot):
    scene = Scene()
    qtbot.addWidget(scene)
    scene.add_action("Not this one")

    scene.set_item(SceneItem("Dune", "2021 · Denis Villeneuve"))

    assert scene._title.text() == "Dune"
    assert scene._destination.isHidden()
    assert scene._warning.isHidden()

    scene.set_item(SceneItem("?", warning="I do not know.", destination="/media/x"))

    assert not scene._warning.isHidden()
    assert not scene._destination.isHidden()


def test_scene_takes_the_color_of_the_image(qtbot):
    scene = Scene()
    qtbot.addWidget(scene)
    image = QImage(20, 30, QImage.Format.Format_RGB32)
    image.fill(QColor(10, 120, 200))

    scene.set_item(SceneItem("Blue", image=QPixmap.fromImage(image)))

    assert scene.color == QColor(10, 120, 200)
