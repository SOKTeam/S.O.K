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
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QWidget

from sok.ui.dialogs.update_dialog import UpdateDialog
from sok.ui.theme import Theme

NOTES = "## Bug Fixes\n\n* **ui:** cancel the previous search"


@pytest.fixture
def manager():
    m = MagicMock()
    m.get_release_notes.return_value = NOTES
    return m


@pytest.mark.parametrize("colors", [Theme.LIGHT, Theme.DARK])
def test_dialog_opens_with_the_theme_colors(qtbot, manager, colors):
    """The dialog used to raise KeyError: 'button_secondary', so the update
    prompt never appeared."""
    window = QWidget()
    window.c = colors
    qtbot.addWidget(window)

    dialog = UpdateDialog(window, manager, "1.4.0")  # deleted with window

    assert colors["bg"] in dialog.styleSheet()
    assert "1.4.0" in dialog.windowTitle()


def test_release_notes_are_rendered_as_markdown(qtbot, manager):
    dialog = UpdateDialog(None, manager, "1.4.0")
    qtbot.addWidget(dialog)

    text = dialog.changelog.toPlainText()
    assert "Bug Fixes" in text
    assert "##" not in text and "**" not in text
