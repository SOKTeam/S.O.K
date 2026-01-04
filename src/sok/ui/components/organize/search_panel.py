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
Search widget for the organization page.

Encapsulates the search bar, results, and media selection.
"""

import logging
from typing import Optional, Dict, Any, List

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QComboBox,
    QPushButton,
)
from PySide6.QtCore import Qt, QTimer, Signal

from sok.ui.theme import card_shadow
from sok.ui.components.base import Card
from sok.ui.components.inputs import SearchBar
from sok.ui.components.window import StopPropagationScrollArea
from sok.ui.components.search import SearchResultRow, SelectedMediaWidget
from sok.ui.i18n import tr

logger = logging.getLogger(__name__)

MAX_RESULT_ROWS = 20
RESULT_ROW_HEIGHT = 51
RESULT_MAX_HEIGHT = 280


class SearchPanel(QWidget):
    """
    Standalone search panel for the organization page.

    This component encapsulates all media search logic:
    - Search bar with debounce (400ms)
    - Content type selector (TV/Movie, Album/Artist, etc.)
    - Results display in scrollable list
    - Selected media widget

    Attributes:
        _media_type (str): Media type ('video', 'music', 'book', 'game')
        _auto_select (bool): If True, automatically selects the first result
        _selected_media (dict | None): Currently selected media data
        _content_type (str): Current content type ('tv', 'movie', 'album', etc.)

    Signals:
        media_selected(dict, str): Emitted when a media is selected.
            - dict: Media data (id, name, year, poster_path, etc.)
            - str: Content type ('tv', 'movie', 'album', 'artist', 'book', 'game')
        search_started(str): Emitted when a search is started.
            - str: Search query text
        type_changed(str): Emitted when content type changes.
            - str: New selected content type

    Example:
        >>> panel = SearchPanel("video")
        >>> panel.search_started.connect(lambda q: print(f"Searching: {q}"))
        >>> panel.media_selected.connect(lambda d, t: print(f"Selected: {d['name']}"))
        >>> panel.set_search_text("Breaking Bad", auto_select=True)
    """

    media_selected = Signal(dict, str)
    search_started = Signal(str)
    type_changed = Signal(str)

    def __init__(self, media_type: str, parent: Optional[QWidget] = None):
        """Initialize the search panel.

        Args:
            media_type: Type of media ('video', 'music', 'book', 'game').
            parent: Parent widget.
        """
        super().__init__(parent)
        self._media_type = media_type
        self._auto_select = False
        self._selected_media: Optional[Dict[str, Any]] = None
        self._content_type = self._get_default_content_type()

        self._build_ui()
        self._setup_timer()

    def _get_default_content_type(self) -> str:
        """Get the default content type based on media type.

        Returns:
            Default content type string.
        """
        defaults = {"video": "tv", "music": "album", "book": "book", "game": "game"}
        return defaults.get(self._media_type, "tv")

    def _build_ui(self):
        """Builds the search panel interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        search_card = Card()
        search_row = QWidget()
        search_row.setFixedHeight(44)
        sr_layout = QHBoxLayout(search_row)
        sr_layout.setContentsMargins(12, 8, 12, 8)

        self._type_combo = QComboBox()
        self._type_combo.setFixedWidth(100)
        self._type_combo.setObjectName("TypeCombo")
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        self._populate_type_combo()
        sr_layout.addWidget(self._type_combo)

        self._search_input = SearchBar("")
        self._search_input.setFixedHeight(28)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        sr_layout.addWidget(self._search_input)

        search_btn = QPushButton(tr("go", "Go"))
        search_btn.setObjectName("SmallBtn")
        search_btn.setFixedSize(40, 28)
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.clicked.connect(self._on_manual_search)
        sr_layout.addWidget(search_btn)

        search_card.add(search_row)
        search_card.setGraphicsEffect(card_shadow())
        layout.addWidget(search_card)

        self._status_label = QLabel("")
        self._status_label.setObjectName("EmptyState")
        layout.addWidget(self._status_label)

        self._results_container = Card()
        self._results_container.setMaximumHeight(320)
        self._results_container.setVisible(False)
        self._results_container.setGraphicsEffect(card_shadow())

        self._results_scroll = StopPropagationScrollArea()
        self._results_scroll.setWidgetResizable(True)
        self._results_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._results_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._results_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._results_scroll.setStyleSheet("background: transparent;")

        self._results_card = Card()
        self._results_card.setObjectName("InnerCard")
        self._results_layout = self._results_card._layout

        self._results_scroll.setWidget(self._results_card)
        self._results_container._layout.addWidget(self._results_scroll)
        layout.addWidget(self._results_container)

        self._media_card = Card()
        self._selected_widget = SelectedMediaWidget()
        self._media_card.add(self._selected_widget)
        self._media_card.setGraphicsEffect(card_shadow())
        layout.addWidget(self._media_card)

    def _populate_type_combo(self):
        """Fill the ComboBox with available types."""
        self._type_combo.blockSignals(True)
        self._type_combo.clear()

        if self._media_type == "video":
            self._type_combo.addItem(tr("tv_series", "TV Series"), "tv")
            self._type_combo.addItem(tr("movie", "Movie"), "movie")
        elif self._media_type == "music":
            self._type_combo.addItem(tr("album", "Album"), "album")
            self._type_combo.addItem(tr("artist", "Artist"), "artist")
        elif self._media_type == "book":
            self._type_combo.addItem(tr("book", "Book"), "book")
        elif self._media_type == "game":
            self._type_combo.addItem(tr("game", "Game"), "game")

        self._type_combo.blockSignals(False)

    def _setup_timer(self):
        """Configure the debounce timer for search."""
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(400)
        self._search_timer.timeout.connect(self._emit_search)

    def _on_type_changed(self, index: int):
        """Handle content type change.

        Args:
            index: Selected combo box index.
        """
        self._content_type = (
            self._type_combo.currentData() or self._get_default_content_type()
        )
        self.type_changed.emit(self._content_type)

        query = self._search_input.text().strip()
        if len(query) >= 2:
            self._search_timer.stop()
            self._emit_search()

    def _on_search_text_changed(self, text: str):
        """Handle search text change.

        Args:
            text: Current search text.
        """
        self._auto_select = False
        if len(text.strip()) >= 2:
            self._search_timer.start()
        else:
            self._search_timer.stop()
            self.clear_results()
            self._status_label.setText("")

    def _on_manual_search(self):
        """Handle manual search via button click."""
        self._auto_select = False
        self._emit_search()

    def _emit_search(self):
        """Emit the search signal."""
        query = self._search_input.text().strip()
        if query:
            self._status_label.setText(tr("searching", "Searching..."))
            self.clear_results()
            self.search_started.emit(query)

    def clear_results(self):
        """Clear the results list."""
        while self._results_layout.count() > 0:
            item = self._results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()  # type: ignore[union-attr]
        self._results_container.setVisible(False)

    def display_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Displays search results in the scrollable container.

        Args:
            results: List of dictionaries containing media data.
                Each dict must contain at minimum 'id' and 'name'.

        Behavior:
            - If results is empty, displays "No results"
            - If auto_select is active, selects the first result
            - Limits display to MAX_RESULT_ROWS (20) items
            - Dynamically adjusts container height
        """
        self.clear_results()

        auto_select = self._auto_select
        self._auto_select = False

        if not results:
            self._status_label.setText(tr("no_results", "No results"))
            return

        self._status_label.setText(f"{len(results)} {tr('results_count', 'result(s)')}")

        if auto_select:
            self._on_result_clicked(results[0])
            return

        self._results_container.setVisible(True)

        display_count = 0
        for data in results[:MAX_RESULT_ROWS]:
            row = SearchResultRow(data, self._content_type)
            row.clicked.connect(lambda d=data: self._on_result_clicked(d))
            self._results_card.add(row)
            display_count += 1

        self._results_layout.addStretch()

        content_height = display_count * RESULT_ROW_HEIGHT
        final_height = min(max(content_height, RESULT_ROW_HEIGHT), RESULT_MAX_HEIGHT)
        self._results_container.setFixedHeight(final_height)

    def display_error(self, error: str):
        """Display a search error.

        Args:
            error: Error message to display.
        """
        self._auto_select = False
        self._status_label.setText(f"{tr('error_prefix', 'Error:')} {error}")

    def _on_result_clicked(self, data: Dict[str, Any]):
        """Handle result click.

        Args:
            data: Selected media data.
        """
        self._selected_media = data
        self.clear_results()
        self._status_label.setText("")
        self._selected_widget.set_media(data, self._content_type)
        self.media_selected.emit(data, self._content_type)

    def set_search_text(self, text: str, auto_select: bool = False) -> None:
        """
        Sets the search text programmatically.

        Args:
            text: Text to place in the search bar.
            auto_select: If True, automatically triggers the search and
                selects the first result.

        Note:
            Search bar signals are blocked during modification
            to avoid infinite loops.
        """
        self._auto_select = auto_select
        self._search_input.blockSignals(True)
        self._search_input.setText(text)
        self._search_input.blockSignals(False)
        if auto_select and text:
            self._emit_search()

    def set_type_by_data(self, data_value: str):
        """Select the content type by its data value.

        Args:
            data_value: Data value to select.
        """
        idx = self._type_combo.findData(data_value)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)

    def get_content_type(self) -> str:
        """Get the selected content type.

        Returns:
            Content type string.
        """
        return self._content_type

    def get_selected_media(self) -> Optional[Dict[str, Any]]:
        """Get the selected media.

        Returns:
            Selected media data or None.
        """
        return self._selected_media

    def update_selected_media(self, details: Dict[str, Any]):
        """Update the details of the selected media.

        Args:
            details: Additional details to merge.
        """
        if self._selected_media:
            self._selected_media.update(details)

    def set_status(self, text: str):
        """Set the status text.

        Args:
            text: Status message to display.
        """
        self._status_label.setText(text)

    def reset(self) -> None:
        """
        Completely resets the search panel.

        Performs the following actions:
        - Clears the search bar
        - Clears all displayed results
        - Deselects the current media
        - Resets the selected media widget
        - Clears the status message
        """
        self._search_input.blockSignals(True)
        self._search_input.setText("")
        self._search_input.blockSignals(False)
        self.clear_results()
        self._selected_media = None
        self._selected_widget.set_media(None, "")  # type: ignore[arg-type]
        self._status_label.setText("")

    def retranslate_ui(self):
        """Updates texts after a language change."""
        self._search_input.setPlaceholderText(tr("search_placeholder", "Search..."))
        current_data = self._type_combo.currentData()
        self._populate_type_combo()
        for i in range(self._type_combo.count()):
            if self._type_combo.itemData(i) == current_data:
                self._type_combo.setCurrentIndex(i)
                break
