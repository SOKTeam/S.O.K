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
from PySide6.QtWidgets import QWidget

from sok.ui import platform


@pytest.fixture
def alerts(monkeypatch):
    calls = []
    monkeypatch.setattr(
        platform.QApplication, "alert", staticmethod(lambda w, *a: calls.append(w))
    )
    return calls


@pytest.fixture
def child(qtbot):
    window = QWidget()
    qtbot.addWidget(window)
    widget = QWidget(window)
    yield widget
    del window


def test_bounces_the_dock_icon_in_the_background(child, alerts, monkeypatch):
    monkeypatch.setattr(platform, "IS_MACOS", True)

    platform.request_attention(child)

    assert alerts == [child.window()]


def test_does_nothing_when_the_window_is_active(child, alerts, monkeypatch):
    monkeypatch.setattr(platform, "IS_MACOS", True)
    monkeypatch.setattr(QWidget, "isActiveWindow", lambda self: True)

    platform.request_attention(child)

    assert alerts == []


def test_does_nothing_on_other_platforms(child, alerts, monkeypatch):
    monkeypatch.setattr(platform, "IS_MACOS", False)

    platform.request_attention(child)

    assert alerts == []
