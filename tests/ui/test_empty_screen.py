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
"""The empty screen of the media pages (mockup 05)."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFocusEvent

from sok.file_operations import GameFileOperations
from sok.ui.components.base import KeyButton
from sok.ui.pages import batch_page
from sok.ui.pages.games_page import CONSOLES, GamesPage
from sok.ui.pages.movies_page import MoviesPage


class FakeConfig:
    def __init__(self, language):
        self.language = language

    def get(self, key, default=None):
        return self.language if key == "language" else default


def test_every_console_read_from_a_name_has_a_short_name():
    assert set(GameFileOperations.PLATFORMS.values()) <= set(CONSOLES)


def test_the_games_page_lists_the_consoles(qtbot):
    page = GamesPage()
    qtbot.addWidget(page)

    label, tags = page.known_tags()

    assert tags == list(CONSOLES.values())
    assert str(len(CONSOLES)) in label


def test_the_other_pages_list_their_formats(qtbot):
    page = MoviesPage()
    qtbot.addWidget(page)

    label, tags = page.known_tags()

    assert "MKV" in tags and "MP4" in tags
    assert str(len(tags)) in label


def test_the_guide_is_in_the_language_of_the_app(monkeypatch):
    monkeypatch.setattr(batch_page, "get_config_manager", lambda: FakeConfig("en"))
    assert batch_page.guide_url() == f"{batch_page.SITE_URL}/guide"
    monkeypatch.setattr(batch_page, "get_config_manager", lambda: FakeConfig("fr"))
    assert batch_page.guide_url() == f"{batch_page.SITE_URL}/fr/guide"


def test_the_focus_ring_of_a_key_is_for_the_keyboard_only(qtbot):
    key = KeyButton("Go")
    qtbot.addWidget(key)

    key.focusInEvent(
        QFocusEvent(QFocusEvent.Type.FocusIn, Qt.FocusReason.OtherFocusReason)
    )
    assert not key._keyboard_focus
    key.focusInEvent(
        QFocusEvent(QFocusEvent.Type.FocusIn, Qt.FocusReason.TabFocusReason)
    )
    assert key._keyboard_focus
    assert not key.testAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect)
