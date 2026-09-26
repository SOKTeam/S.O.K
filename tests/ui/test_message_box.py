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
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QWidget

from sok.ui import message_box
from sok.ui.message_box import StandardButton


@pytest.fixture
def window(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def shown(monkeypatch):
    """Record the boxes shown on macOS instead of blocking on exec()."""
    boxes = []

    def fake_exec(box):
        boxes.append(box)
        return StandardButton.Yes

    monkeypatch.setattr(message_box, "IS_MACOS", True)
    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    return boxes


class TestOnMacOS:
    def test_question_is_a_sheet_of_the_window(self, window, shown):
        child = QWidget(window)

        answer = message_box.question(child, "Title", "Rename?")

        assert answer == StandardButton.Yes
        (box,) = shown
        assert box.parent() is window
        assert box.windowModality() == Qt.WindowModality.WindowModal

    def test_default_button_is_kept(self, window, shown):
        message_box.question(
            window,
            "Title",
            "Reset?",
            StandardButton.Yes | StandardButton.No,
            StandardButton.No,
        )

        (box,) = shown
        assert box.defaultButton() is box.button(StandardButton.No)

    def test_warning_keeps_its_icon(self, window, shown):
        message_box.warning(window, "Title", "Careful")

        (box,) = shown
        assert box.icon() == QMessageBox.Icon.Warning

    def test_as_sheet_without_parent_does_nothing(self, shown):
        box = QMessageBox()
        modality = box.windowModality()

        message_box.as_sheet(box, None)

        assert box.windowModality() == modality


class TestRevealInFinder:
    @pytest.fixture
    def opened(self, monkeypatch):
        urls = []
        monkeypatch.setattr(
            message_box.QDesktopServices, "openUrl", staticmethod(urls.append)
        )
        return urls

    def click_reveal(self, monkeypatch):
        def fake_exec(box):
            (reveal,) = [
                b
                for b in box.buttons()
                if box.buttonRole(b) == QMessageBox.ButtonRole.ActionRole
            ]
            reveal.click()
            return 0

        monkeypatch.setattr(message_box, "IS_MACOS", True)
        monkeypatch.setattr(QMessageBox, "exec", fake_exec)

    def test_reveal_button_opens_the_folder(
        self, window, monkeypatch, opened, tmp_path
    ):
        self.click_reveal(monkeypatch)

        message_box.information(window, "Title", "Done", reveal=tmp_path)

        assert [url.toLocalFile() for url in opened] == [str(tmp_path)]

    def test_no_reveal_button_without_folder(self, window, shown):
        message_box.information(window, "Title", "Done")

        (box,) = shown
        roles = [box.buttonRole(b) for b in box.buttons()]
        assert QMessageBox.ButtonRole.ActionRole not in roles


class TestOnOtherPlatforms:
    @pytest.mark.parametrize("kind", ["information", "warning", "critical", "question"])
    def test_calls_the_qt_static_function(self, window, monkeypatch, kind):
        monkeypatch.setattr(message_box, "IS_MACOS", False)
        calls = []
        monkeypatch.setattr(
            QMessageBox,
            kind,
            lambda *args: calls.append(args) or StandardButton.Ok,
        )

        getattr(message_box, kind)(window, "Title", "Text")

        assert calls[0][:3] == (window, "Title", "Text")

    def test_as_sheet_does_nothing(self, window, monkeypatch):
        monkeypatch.setattr(message_box, "IS_MACOS", False)
        box = QMessageBox()

        message_box.as_sheet(box, window)

        assert box.parent() is None
