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
import time

import pytest
import shiboken6

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QWidget

# Import the widget to test
from sok.ui.components import search
from sok.ui.components.search import load_poster


def _png_bytes() -> bytes:
    """Return a small valid PNG image."""
    pm = QPixmap(4, 4)
    pm.fill(QColor("orange"))
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pm.save(buf, "PNG")
    return bytes(data.data())


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Serve posters from memory instead of downloading them."""
    png = _png_bytes()  # Built here: QPixmap must stay in the GUI thread.
    monkeypatch.setattr(search, "_download", lambda url: png)
    search._cache.clear()
    search._pending.clear()
    search._waiters.clear()


class TestLoadPoster:
    def test_delivers_scaled_pixmap(self, qtbot):
        """The poster reaches its widget in the GUI thread, scaled."""
        widget = QWidget()
        received = []
        load_poster("https://example.com/a.png", 10, 10, widget, received.append)
        qtbot.waitUntil(lambda: bool(received), timeout=2000)
        assert received[0].width() == 10

    def test_deleted_widget_is_skipped(self, qtbot, monkeypatch):
        """A widget deleted before its poster arrives is never called back."""
        png = _png_bytes()

        def slow(url):
            time.sleep(0.1)
            return png

        monkeypatch.setattr(search, "_download", slow)
        widget = QWidget()
        received = []
        load_poster("https://example.com/a.png", 10, 10, widget, received.append)
        shiboken6.delete(widget)
        qtbot.wait(300)
        assert received == []

    def test_deliver_checks_the_widget_still_exists(self, qapp):
        """Delivery to a deleted widget is dropped instead of crashing."""
        widget = QWidget()
        shiboken6.delete(widget)
        received = []
        search._deliver(widget, received.append, _png_bytes(), (10, 10))
        assert received == []
