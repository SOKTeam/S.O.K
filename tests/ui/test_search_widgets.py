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
from unittest.mock import patch

# Import the widget to test
from sok.ui.components.search import SelectedMediaWidget
from sok.ui.controllers.worker_runner import WorkerRunner


@pytest.fixture(autouse=True)
def no_threads(monkeypatch):
    """Avoid spinning real QThreads in tests to prevent teardown warnings."""

    def _run_stub(self, worker, on_finished, on_error, on_progress=None):
        try:
            if on_finished:
                on_finished(None)
        finally:
            self._thread = None
            self._current_worker = None
        return worker

    monkeypatch.setattr(WorkerRunner, "run", _run_stub)


class TestSearchWidgets:
    def test_selected_media_widget_initial_state(self, qapp):
        """Test that the widget starts in empty state."""
        widget = SelectedMediaWidget()

        # Check internal state
        assert widget._data is None
        assert widget._type is None
        assert widget._empty is True

    @patch("urllib.request.urlopen")  # Mock network call for poster
    def test_selected_media_widget_set_media(self, mock_urlopen, qtbot):
        """Test setting media data updates the widget state."""
        widget = SelectedMediaWidget()

        # Mock data
        movie_data = {
            "title": "Test Movie",
            "release_date": "2023-01-01",
            "poster_path": "/path.jpg",
        }

        # Setup mock for image download
        # We simulate a small valid image response (not strictly necessary if we mock _load_poster,
        # but mocking urlopen is closer to integration)
        # However, to be safe and avoid QPixmap errors with garbage data,
        # let's just mock _load_poster directly if possible, OR just check the data state.

        # Let's verify data state logic first.
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
