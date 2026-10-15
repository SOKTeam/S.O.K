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
import threading
import time

import pytest
import shiboken6

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QWidget

# Import the widget to test
from sok.ui.components import search
from sok.ui.components.search import SearchResultRow, SelectedMediaWidget, load_poster


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


class TestSearchWidgets:
    def test_selected_media_widget_initial_state(self, qapp):
        """Test that the widget starts in empty state."""
        widget = SelectedMediaWidget()

        # Check internal state
        assert widget._data is None
        assert widget._type is None
        assert widget._empty is True

    def test_selected_media_widget_set_media(self, qtbot):
        """Test setting media data updates the widget state."""
        widget = SelectedMediaWidget()

        # Mock data
        movie_data = {
            "title": "Test Movie",
            "release_date": "2023-01-01",
            "poster_path": "/path.jpg",
        }

        widget.set_media(movie_data, "movie")

        assert widget._data == movie_data
        assert widget._type == "movie"
        assert widget._empty is False

        # Verify clear
        widget.clear()
        assert widget._data is None
        assert widget._empty is True

    def test_selected_media_widget_tv_logic(self, qtbot):
        """Test specific logic for TV shows (name vs title)."""
        widget = SelectedMediaWidget()
        tv_data = {"name": "Test Show", "first_air_date": "2020-05-05"}

        widget.set_media(tv_data, "tv")
        assert widget._data is not None
        assert widget._data["name"] == "Test Show"
        assert widget._type == "tv"


# APIs return null for unknown fields: Deezer albums without a release date.
NULL_FIELDS = {"title": None, "name": None, "release_date": None}


@pytest.mark.parametrize("content_type", ["album", "movie", "tv", "artist"])
def test_selected_media_paints_with_null_fields(qtbot, content_type):
    widget = SelectedMediaWidget()
    qtbot.addWidget(widget)
    widget.set_media({**NULL_FIELDS, "first_air_date": None}, content_type)

    widget.paintEvent(None)


@pytest.mark.parametrize("content_type", ["album", "movie", "tv"])
def test_search_result_row_paints_with_null_fields(qtbot, content_type):
    row = SearchResultRow({**NULL_FIELDS, "first_air_date": None}, content_type)
    qtbot.addWidget(row)

    row.paintEvent(None)


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

    def test_stale_poster_is_ignored(self, qtbot):
        """A poster of the previous media does not replace the current one."""
        widget = SelectedMediaWidget()
        widget.set_media({"title": "New"}, "movie")
        widget._poster_url = "https://image.tmdb.org/t/p/w92/new.jpg"
        stale = QPixmap(2, 2)
        widget._on_poster_loaded(stale, "https://image.tmdb.org/t/p/w92/old.jpg")
        assert widget._poster is None

    def test_slow_download_is_delivered_in_gui_thread(self, qtbot, monkeypatch):
        """QPixmap is only ever built in the GUI thread."""

        png = _png_bytes()

        def slow(url):
            time.sleep(0.1)
            return png

        monkeypatch.setattr(search, "_download", slow)
        widget = QWidget()
        threads = []
        load_poster(
            "https://example.com/a.png",
            10,
            10,
            widget,
            lambda pm: threads.append(threading.current_thread()),
        )
        qtbot.waitUntil(lambda: bool(threads), timeout=2000)
        assert threads == [threading.main_thread()]

    def test_each_url_is_downloaded_once(self, qtbot, monkeypatch):
        """The selected media reuses the image its result row downloaded."""
        png = _png_bytes()
        calls = []

        def slow(url):
            calls.append(url)
            time.sleep(0.1)
            return png

        monkeypatch.setattr(search, "_download", slow)
        row, selected = QWidget(), QWidget()
        received = []
        load_poster("https://example.com/a.png", 10, 10, row, received.append)
        load_poster("https://example.com/a.png", 20, 20, selected, received.append)
        qtbot.waitUntil(lambda: len(received) == 2, timeout=2000)

        later = []
        load_poster("https://example.com/a.png", 30, 30, QWidget(), later.append)
        assert calls == ["https://example.com/a.png"]
        assert [pm.width() for pm in received + later] == [10, 20, 30]

    def test_download_continues_for_remaining_widget(self, qtbot, monkeypatch):
        """Deleting the row does not cancel the image the selection waits for."""
        png = _png_bytes()

        def slow(url):
            time.sleep(0.1)
            return png

        monkeypatch.setattr(search, "_download", slow)
        row, selected = QWidget(), QWidget()
        received = []
        load_poster("https://example.com/a.png", 10, 10, row, lambda pm: None)
        load_poster("https://example.com/a.png", 20, 20, selected, received.append)
        shiboken6.delete(row)
        qtbot.waitUntil(lambda: bool(received), timeout=2000)
        assert received[0].width() == 20
