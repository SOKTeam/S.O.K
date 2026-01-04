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
Custom Dialogs for S.O.K
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QScrollArea,
    QFrame,
    QWidget,
)
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QFont, QPainterPath

from sok.ui.theme import Theme
from sok.ui.components.base import parse_color, ActionButton
from sok.ui.components.inputs import SearchBar
from sok.ui.workers import SearchWorker
from sok.ui.i18n import tr
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.components.search import ImageLoaderWorker


class SearchResultCard(QFrame):
    """Result card for search dialog.

    Displays a search result with poster, title, and metadata.

    Attributes:
        clicked: Signal emitted with result data when clicked.
        _data: Result data dictionary.
        _type: Content type (tv, movie, album, etc.).
        _poster: Loaded poster pixmap.
    """

    clicked = Signal(dict)

    def __init__(self, data: dict, content_type: str, parent=None):
        """Initialize the search result card.

        Args:
            data: Result data dictionary.
            content_type: Type of content.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._data = data
        self._type = content_type
        self._hover = False
        self._poster = None
        self._runner = WorkerRunner(self)

        self._is_music = self._type in ("album", "artist")
        self._pw, self._ph = (64, 64) if self._is_music else (50, 75)

        self.setFixedHeight(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        poster_path = data.get("poster_path")
        if poster_path:
            url = (
                poster_path
                if poster_path.startswith("http")
                else f"https://image.tmdb.org/t/p/w92{poster_path}"
            )
            worker = ImageLoaderWorker(url, self._pw, self._ph)
            self._runner.run(worker, self._on_poster_loaded, lambda _err: None)

    def _on_poster_loaded(self, pm):
        """Handle poster image loaded.

        Args:
            pm: Loaded pixmap.
        """
        self._poster = pm
        self.update()

    def closeEvent(self, event):
        """Handle widget close.

        Args:
            event: Close event.
        """
        self._runner.stop()
        super().closeEvent(event)

    def enterEvent(self, e):
        """Handle mouse enter.

        Args:
            e: Enter event.
        """
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        """Handle mouse leave.

        Args:
            e: Leave event.
        """
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        """Handle mouse click.

        Args:
            e: Mouse event.
        """
        self.clicked.emit(self._data)

    def paintEvent(self, e):
        """Paint the card.

        Args:
            e: Paint event.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        c = Theme.DARK
        if hasattr(self.window(), "c"):
            c = self.window().c  # type: ignore[union-attr]

        bg_color = c["tertiary"] if self._hover else c["card"]

        p.setBrush(parse_color(bg_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)

        x, py = 12, (self.height() - self._ph) // 2

        if self._poster:
            if self._is_music:
                p.save()
                path = QPainterPath()
                path.addRoundedRect(x, py, self._pw, self._ph, 6, 6)
                p.setClipPath(path)
                p.drawPixmap(x, py, self._poster)
                p.restore()
            else:
                p.drawPixmap(x, py, self._poster)
            x += self._pw + 10
        else:
            p.setBrush(parse_color(c["tertiary"]))
            p.drawRoundedRect(x, py, self._pw, self._ph, 4, 4)
            x += self._pw + 10

        title = self._data.get("title") or self._data.get(
            "name", tr("unknown", "Inconnu")
        )
        p.setPen(parse_color(c["text"]))
        p.setFont(QFont(Theme.FONT, 13, QFont.Weight.Bold))
        p.drawText(
            QRect(x, 8, self.width() - x - 12, 20), Qt.AlignmentFlag.AlignVCenter, title
        )

        info_parts = []
        if self._type == "tv":
            fa = self._data.get("first_air_date", "")[:4]
            if fa:
                info_parts.append(fa)
            info_parts.append(tr("tv_series", "TV Series"))
        elif self._type == "movie":
            rd = self._data.get("release_date", "")[:4]
            if rd:
                info_parts.append(rd)
            info_parts.append(tr("movie", "Movie"))
        elif self._type == "album":
            rd = self._data.get("release_date", "")[:4]
            if rd:
                info_parts.append(rd)
            info_parts.append(tr("album", "Album"))
        elif self._type == "artist":
            info_parts.append(tr("artist", "Artist"))

        p.setPen(parse_color(c["secondary"]))
        p.setFont(QFont(Theme.FONT, 11))
        p.drawText(
            QRect(x, 28, self.width() - x - 12, 18),
            Qt.AlignmentFlag.AlignVCenter,
            " · ".join(info_parts),
        )

        raw_overview = self._data.get("overview", "")
        ov = (raw_overview[:100] + "...") if len(raw_overview) > 100 else raw_overview

        p.setFont(QFont(Theme.FONT, 10))
        p.drawText(
            QRect(x, 48, self.width() - x - 12, 28),
            Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
            ov,
        )


class SearchResultsDialog(QDialog):
    """Dialog for TMDB search results.

    Provides a search interface for finding media on TMDB.

    Attributes:
        selected: Signal emitted with (data, type) when result selected.
        _results: List of search results.
        _type: Current content type filter.
    """

    selected = Signal(dict, str)

    def __init__(self, parent=None):
        """Initialize the search results dialog.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._results = []
        self._type = "tv"
        self.c = (
            parent.window().c
            if parent and hasattr(parent, "window") and hasattr(parent.window(), "c")
            else Theme.DARK
        )
        self._runner = WorkerRunner(self)

        self.resize(500, 450)
        self.setModal(True)

        self._build()
        self.retranslateUi()

    def _build(self):
        """Build the dialog UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        type_row = QHBoxLayout()

        self._tv_btn = QPushButton()
        self._tv_btn.setCheckable(True)
        self._tv_btn.setChecked(True)
        self._tv_btn.setObjectName("TypeBtn")
        self._tv_btn.clicked.connect(lambda: self._set_type("tv"))

        self._movie_btn = QPushButton()
        self._movie_btn.setCheckable(True)
        self._movie_btn.setObjectName("TypeBtn")
        self._movie_btn.clicked.connect(lambda: self._set_type("movie"))

        type_row.addWidget(self._tv_btn)
        type_row.addWidget(self._movie_btn)
        type_row.addStretch()
        layout.addLayout(type_row)

        # Search Input
        search_row = QHBoxLayout()
        self._search = SearchBar()
        self._search.returnPressed.connect(self._do_search)
        search_row.addWidget(self._search)

        self._search_btn = ActionButton()
        self._search_btn.setFixedWidth(100)
        self._search_btn.clicked.connect(self._do_search)
        search_row.addWidget(self._search_btn)

        layout.addLayout(search_row)

        self._status = QLabel("")
        self._status.setObjectName("EmptyState")
        layout.addWidget(self._status)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setObjectName("Page")
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._results_widget = QWidget()
        self._results_widget.setObjectName("PageContent")

        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setContentsMargins(0, 0, 8, 12)
        self._results_layout.setSpacing(8)
        self._results_layout.addStretch()

        self._scroll.setWidget(self._results_widget)
        layout.addWidget(self._scroll, 1)

    def retranslateUi(self):
        """Update translatable UI text."""
        self.setWindowTitle(tr("search_results", "Search Results"))
        self._tv_btn.setText(tr("tv_series", "TV Series"))
        self._movie_btn.setText(tr("movie", "Movies"))
        self._search.setPlaceholderText(tr("search_tmdb", "Search on TMDB..."))
        self._search_btn.setText(tr("search", "Search"))

        if self._status.text() == "Searching...":
            self._status.setText(tr("searching", "Searching..."))

    def _set_type(self, t: str):
        """Set the content type filter.

        Args:
            t: Content type ('tv' or 'movie').
        """
        self._type = t
        self._tv_btn.setChecked(t == "tv")
        self._movie_btn.setChecked(t == "movie")

    def _do_search(self):
        """Execute the search query."""
        query = self._search.text().strip()
        if not query:
            return

        self._status.setText(tr("searching", "Searching..."))
        self._clear_results()

        worker = SearchWorker(query, self._type)
        self._runner.run(worker, self._on_results, self._on_error)

    def _clear_results(self):
        """Clear all result cards from the layout."""
        while self._results_layout.count() > 1:
            it = self._results_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()  # type: ignore[union-attr]

    def _on_results(self, res: list):
        """Handle search results.

        Args:
            res: List of search result dictionaries.
        """
        self._clear_results()
        if not res:
            self._status.setText(tr("no_results", "No results"))
            return

        self._status.setText(f"{len(res)} {tr('results_count', 'result(s)')}")

        for d in res:
            card = SearchResultCard(d, self._type)
            card.clicked.connect(lambda data=d: self._on_select(data))
            self._results_layout.insertWidget(self._results_layout.count() - 1, card)

    def _on_error(self, err: str):
        """Handle search error.

        Args:
            err: Error message.
        """
        self._status.setText(f"{tr('error_prefix', 'Error:')} {err}")

    def _on_select(self, data: dict):
        """Handle result selection.

        Args:
            data: Selected result data.
        """
        self.selected.emit(data, self._type)
        self.accept()

    def closeEvent(self, event):
        """Handle dialog close.

        Args:
            event: Close event.
        """
        self._runner.stop()
        super().closeEvent(event)
