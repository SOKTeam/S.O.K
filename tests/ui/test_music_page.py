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
from sok.ui.pages.music_page import MusicPage


def test_switch_shows_albums_then_tracks(qtbot):
    page = MusicPage()
    qtbot.addWidget(page)

    assert page.current() is page.albums

    page.show_tracks()

    assert page.current() is page.tracks
    assert page._albums_btn.isChecked() is False
