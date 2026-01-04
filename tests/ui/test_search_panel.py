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
"""
Tests unitaires pour le composant SearchPanel.

Ces tests vérifient le comportement isolé du panel de recherche,
indépendamment de la page d'organisation.
"""
from sok.ui.components.organize import SearchPanel


class TestSearchPanelInitialization:
    """Tests d'initialisation du SearchPanel."""

    def test_init_video_type(self, qtbot):
        """Test initialization with video media type."""
        panel = SearchPanel("video")

        assert panel._media_type == "video"
        assert panel._content_type == "tv"  # Default for video
        assert panel._selected_media is None
        assert panel._auto_select is False

    def test_init_music_type(self, qtbot):
        """Test initialization with music media type."""
        panel = SearchPanel("music")

        assert panel._media_type == "music"
        assert panel._content_type == "album"  # Default for music

    def test_init_book_type(self, qtbot):
        """Test initialization with book media type."""
        panel = SearchPanel("book")

        assert panel._media_type == "book"
        assert panel._content_type == "book"

    def test_init_game_type(self, qtbot):
        """Test initialization with game media type."""
        panel = SearchPanel("game")

        assert panel._media_type == "game"
        assert panel._content_type == "game"


class TestSearchPanelPublicAPI:
    """Tests de l'API publique du SearchPanel."""

    def test_get_content_type_returns_current_type(self, qtbot):
        """Test that get_content_type returns the current selection."""
        panel = SearchPanel("video")

        assert panel.get_content_type() == "tv"

    def test_get_selected_media_returns_none_initially(self, qtbot):
        """Test that get_selected_media returns None when nothing selected."""
        panel = SearchPanel("video")

        assert panel.get_selected_media() is None

    def test_set_type_by_data_changes_content_type(self, qtbot):
        """Test setting content type by data value."""
        panel = SearchPanel("video")

        panel.set_type_by_data("movie")
        assert panel._content_type == "movie"

        panel.set_type_by_data("tv")
        assert panel._content_type == "tv"

    def test_set_type_by_data_ignores_invalid_value(self, qtbot):
        """Test that invalid type values are ignored."""
        panel = SearchPanel("video")
        original_type = panel._content_type

        panel.set_type_by_data("invalid_type")
        assert panel._content_type == original_type

    def test_set_search_text_updates_input(self, qtbot):
        """Test setting search text programmatically."""
        panel = SearchPanel("video")

        panel.set_search_text("Breaking Bad")
        assert panel._search_input.text() == "Breaking Bad"

    def test_set_status_updates_label(self, qtbot):
        """Test setting status message."""
        panel = SearchPanel("video")

        panel.set_status("Recherche en cours...")
        assert panel._status_label.text() == "Recherche en cours..."

    def test_update_selected_media_merges_details(self, qtbot):
        """Test that update_selected_media merges new details."""
        panel = SearchPanel("video")
        panel._selected_media = {"id": 123, "name": "Test"}

        panel.update_selected_media({"episodes": {"1x01": "Pilot"}})

        assert panel._selected_media["id"] == 123
        assert panel._selected_media["name"] == "Test"
        assert panel._selected_media["episodes"] == {"1x01": "Pilot"}

    def test_update_selected_media_does_nothing_if_none(self, qtbot):
        """Test that update_selected_media is safe when nothing selected."""
        panel = SearchPanel("video")

        # Should not raise
        panel.update_selected_media({"episodes": {}})
        assert panel._selected_media is None


class TestSearchPanelReset:
    """SearchPanel reset tests."""

    def test_reset_clears_search_input(self, qtbot):
        """Test that reset clears the search input."""
        panel = SearchPanel("video")
        panel._search_input.setText("Some query")

        panel.reset()

        assert panel._search_input.text() == ""

    def test_reset_clears_selected_media(self, qtbot):
        """Test that reset clears selected media."""
        panel = SearchPanel("video")
        panel._selected_media = {"id": 123}

        panel.reset()

        assert panel._selected_media is None

    def test_reset_clears_status(self, qtbot):
        """Test that reset clears status label."""
        panel = SearchPanel("video")
        panel._status_label.setText("Some status")

        panel.reset()

        assert panel._status_label.text() == ""


class TestSearchPanelResults:
    """Results display tests."""

    def test_display_results_empty_shows_no_results(self, qtbot):
        """Test that empty results show appropriate message."""
        panel = SearchPanel("video")

        panel.display_results([])

        # Check for French or English version of "no results"
        text = panel._status_label.text().lower()
        assert (
            "aucun résultat" in text
            or "no results" in text
            or "résultat" in text
            or "result" in text
        )

    def test_display_results_shows_count(self, qtbot):
        """Test that results count is displayed."""
        panel = SearchPanel("video")
        results = [
            {"id": 1, "name": "Show 1"},
            {"id": 2, "name": "Show 2"},
            {"id": 3, "name": "Show 3"},
        ]

        panel.display_results(results)

        assert "3" in panel._status_label.text()

    def test_display_results_makes_container_visible(self, qtbot):
        """Test that results container becomes visible (internal state)."""
        panel = SearchPanel("video")
        results = [{"id": 1, "name": "Test Show"}]

        panel.display_results(results)

        # Check internal visibility flag (widget may not be shown on screen in tests)
        assert (
            panel._results_container.isVisibleTo(panel)
            or not panel._results_container.isHidden()
        )

    def test_clear_results_hides_container(self, qtbot):
        """Test that clear_results hides the results container."""
        panel = SearchPanel("video")
        panel._results_container.setVisible(True)

        panel.clear_results()

        assert not panel._results_container.isVisible()

    def test_display_error_updates_status(self, qtbot):
        """Test that display_error shows error message."""
        panel = SearchPanel("video")

        panel.display_error("Connection failed")

        assert "Connection failed" in panel._status_label.text()
        assert panel._auto_select is False


class TestSearchPanelSignals:
    """SearchPanel signals tests."""

    def test_type_changed_signal_emitted(self, qtbot):
        """Test that type_changed signal is emitted when type changes."""
        panel = SearchPanel("video")
        signal_received = []

        panel.type_changed.connect(lambda t: signal_received.append(t))

        # Change type
        idx = panel._type_combo.findData("movie")
        if idx >= 0:
            panel._type_combo.setCurrentIndex(idx)

        assert "movie" in signal_received

    def test_search_started_signal_emitted(self, qtbot):
        """Test that search_started signal is emitted."""
        panel = SearchPanel("video")
        signal_received = []

        panel.search_started.connect(lambda q: signal_received.append(q))
        panel._search_input.setText("Test Query")

        # Manually trigger search
        panel._emit_search()

        assert "Test Query" in signal_received


class TestSearchPanelAutoSelect:
    """Tests du comportement auto-select."""

    def test_auto_select_flag_set_by_set_search_text(self, qtbot):
        """Test that auto_select flag is set correctly."""
        panel = SearchPanel("video")

        # Track if search was emitted
        search_emitted = []
        panel.search_started.connect(lambda q: search_emitted.append(q))

        panel.set_search_text("Test", auto_select=True)

        # The search should have been triggered
        assert len(search_emitted) == 1
        assert search_emitted[0] == "Test"

    def test_display_results_with_auto_select_emits_media_selected(self, qtbot):
        """Test that auto_select triggers media_selected on first result."""
        panel = SearchPanel("video")
        panel._auto_select = True

        signal_received = []
        panel.media_selected.connect(lambda d, t: signal_received.append((d, t)))

        results = [{"id": 1, "name": "First Result"}]
        panel.display_results(results)

        # Should have selected first result
        assert len(signal_received) == 1
        assert signal_received[0][0]["name"] == "First Result"


class TestSearchPanelRetranslate:
    """Tests de la traduction dynamique."""

    def test_retranslate_ui_preserves_selection(self, qtbot):
        """Test that retranslate_ui preserves the current type selection."""
        panel = SearchPanel("video")

        # Select "movie"
        panel.set_type_by_data("movie")
        original_type = panel._content_type

        # Retranslate
        panel.retranslate_ui()

        # Selection should be preserved
        assert panel._type_combo.currentData() == original_type
