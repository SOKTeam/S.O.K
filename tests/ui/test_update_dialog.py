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


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/x/SOK_Setup_v1.4.0.exe",
        "https://github.com/x/SOK_macOS_v1.4.0.dmg",
        "https://github.com/x/SOK_Linux_v1.4.0_x86_64.AppImage",
    ],
)
def test_installers_are_downloaded_by_the_dialog(qtbot, manager, monkeypatch, url):
    """The .dmg used to open in the browser, which left the download to the
    user while the app kept running."""
    manager.get_download_url.return_value = url
    dialog = UpdateDialog(None, manager, "1.4.0")
    qtbot.addWidget(dialog)
    opened, started = [], []
    monkeypatch.setattr("webbrowser.open", opened.append)
    monkeypatch.setattr(
        dialog._runner, "run", lambda worker, *a: started.append(worker)
    )

    dialog.start_update()

    assert opened == []
    assert started[0].url == url


def test_the_release_page_opens_in_the_browser(qtbot, manager, monkeypatch):
    manager.get_download_url.return_value = "https://github.com/x/releases/tag/v1.4.0"
    dialog = UpdateDialog(None, manager, "1.4.0")
    qtbot.addWidget(dialog)
    opened = []
    monkeypatch.setattr("webbrowser.open", opened.append)

    dialog.start_update()

    assert opened == ["https://github.com/x/releases/tag/v1.4.0"]
