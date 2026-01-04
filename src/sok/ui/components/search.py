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
Search related widgets
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QObject, QRect
from PySide6.QtGui import QPainter, QFont, QPixmap, QPainterPath

from sok.ui.theme import Theme
from sok.ui.components.base import parse_color
from sok.ui.i18n import tr
from sok.ui.controllers.worker_runner import WorkerRunner
import urllib.request
import urllib.error


class ImageLoaderWorker(QObject):
    """Worker for asynchronous image loading.

    Loads images from URLs in a separate thread.

    Signals:
        finished: Emitted with loaded pixmap on success.
        error: Emitted with error message on failure.
    """

    finished = Signal(QPixmap)
    error = Signal(str)

    def __init__(self, url, width, height):
        """Initialize the image loader worker.

        Args:
            url: URL of the image to load.
            width: Target width for scaling.
            height: Target height for scaling.
        """
        super().__init__()
        self.url = url
        self.width = width
        self.height = height
        self._running = True

    def stop(self):
        """Stop the worker."""
        self._running = False

    def run(self):
        """Execute the image loading."""

        try:
            if not self._running:
                return
            with urllib.request.urlopen(self.url, timeout=5) as response:
                if not self._running:
                    return
                data = response.read()
                pm = QPixmap()
                pm.loadFromData(data)
                if not pm.isNull() and self._running:
                    scaled = pm.scaled(
                        self.width,
                        self.height,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self.finished.emit(scaled)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            self.error.emit(str(e))


class SearchResultRow(QWidget):
    """Compact search result with image.

    Displays a search result with poster image, title, and year.

    Signals:
        clicked: Emitted with result data when clicked.
    """

    clicked = Signal(dict)

    def __init__(self, data: dict, content_type: str, parent=None):
        """Initialize the search result row.

        Args:
            data: Search result data dictionary.
            content_type: Type of content (tv, movie, album, artist).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._data = data
        self._type = content_type
        self._hover = False
        self._poster = None
        self._runner = WorkerRunner(self)
        self._is_music = self._type in ("album", "artist")
        self._pw = 40 if self._is_music else 30
        self._ph = 40 if self._is_music else 45
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        poster_path = data.get("poster_path")
        if poster_path:
            url = (
                poster_path
                if poster_path.startswith("http")
                else f"https://image.tmdb.org/t/p/w92{poster_path}"
            )
            self._start_image_loading(url)

    def _start_image_loading(self, url: str):
        """Start asynchronous image loading.

        Args:
            url: Image URL to load.
        """
        worker = ImageLoaderWorker(url, self._pw, self._ph)
        self._runner.run(worker, self._on_poster_loaded, lambda _err: None)

    def _on_poster_loaded(self, pixmap):
        """Handle loaded poster image.

        Args:
            pixmap: Loaded image pixmap.
        """
        self._poster = pixmap
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
        """Handle mouse press.

        Args:
            e: Mouse event.
        """
        self.clicked.emit(self._data)

    def paintEvent(self, e):
        """Paint the search result row.

        Args:
            e: Paint event.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.window().c if hasattr(self.window(), "c") else Theme.DARK  # type: ignore[union-attr]

        if self._hover:
            p.setBrush(parse_color(c["tertiary"]))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(self.rect(), 6, 6)

        x, py = 8, (self.height() - self._ph) // 2
        if self._poster:
            if self._is_music:
                p.save()
                path = QPainterPath()
                path.addRoundedRect(x, py, self._pw, self._ph, 4, 4)
                p.setClipPath(path)
                p.drawPixmap(x, py, self._poster)
                p.restore()
            else:
                p.drawPixmap(x, py, self._poster)
        else:
            p.setBrush(parse_color(c["tertiary"]))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, py, self._pw, self._ph, 3, 3)

        x += self._pw + 8
        title = self._data.get("title") or self._data.get(
            "name", tr("unknown", "Inconnu")
        )
        p.setPen(parse_color(c["text"]))
        p.setFont(QFont(Theme.FONT, 12))
        p.drawText(
            QRect(x, 0, self.width() - x - 60, self.height()),
            Qt.AlignmentFlag.AlignVCenter,
            title,
        )

        year = ""
        if self._type == "tv":
            year = self._data.get("first_air_date", "")[:4]
        elif self._type == "movie":
            year = self._data.get("release_date", "")[:4]
        elif self._type == "album":
            year = self._data.get("release_date", "")[:4]

        if year:
            p.setPen(parse_color(c["secondary"]))
            p.setFont(QFont(Theme.FONT, 11))
            p.drawText(
                QRect(self.width() - 60, 0, 50, self.height()),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                year,
            )


class SelectedMediaWidget(QWidget):
    """Widget showing selected media details.

    Displays poster, title, year, and type of the selected media.
    """

    def __init__(self, parent=None):
        """Initialize the selected media widget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._data: dict | None = None
        self._type: str | None = None
        self._poster = None
        self._empty = True
        self._runner = WorkerRunner(self)
        self.setFixedHeight(60)

    def retranslateUi(self):
        """Update translatable UI text."""
        self.update()

    def set_media(self, data: dict | None, content_type: str):
        """Set the displayed media.

        Args:
            data: Media data dictionary or None to clear.
            content_type: Type of content (tv, movie, album, artist).
        """
        if data is None:
            self.clear()
            return
        self._data, self._type, self._empty, self._poster = (
            data,
            content_type,
            False,
            None,
        )
        self._is_music = self._type in ("album", "artist")
        self._pw, self._ph = (42, 42) if self._is_music else (35, 52)
        poster_path = data.get("poster_path")
        if poster_path:
            url = (
                poster_path
                if poster_path.startswith("http")
                else f"https://image.tmdb.org/t/p/w92{poster_path}"
            )
            self._start_image_loading(url)
        self.update()

    def clear(self):
        """Clear the selected media."""
        self._data, self._type, self._poster, self._empty = None, None, None, True
        self.update()

    def _start_image_loading(self, url: str):
        """Start asynchronous image loading.

        Args:
            url: Image URL to load.
        """
        worker = ImageLoaderWorker(url, self._pw, self._ph)
        self._runner.run(worker, self._on_poster_loaded, lambda _err: None)

    def _on_poster_loaded(self, pixmap):
        """Handle loaded poster image.

        Args:
            pixmap: Loaded image pixmap.
        """
        self._poster = pixmap
        self.update()

    def closeEvent(self, event):
        """Handle widget close.

        Args:
            event: Close event.
        """
        self._runner.stop()
        super().closeEvent(event)

    def paintEvent(self, e):
        """Paint the selected media widget.

        Args:
            e: Paint event.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.window().c if hasattr(self.window(), "c") else Theme.DARK  # type: ignore[union-attr]

        if self._empty:
            p.setPen(parse_color(c["secondary"]))
            p.setFont(QFont(Theme.FONT, 13))
            p.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                tr("no_media_selected", "No media selected"),
            )
            return

        x, py = 12, (self.height() - self._ph) // 2
        if self._poster:
            if self._is_music:
                p.save()
                path = QPainterPath()
                path.addRoundedRect(x, py, self._pw, self._ph, 4, 4)
                p.setClipPath(path)
                p.drawPixmap(x, py, self._poster)
                p.restore()
            else:
                p.drawPixmap(x, py, self._poster)
        else:
            p.setBrush(parse_color(c["tertiary"]))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, py, self._pw, self._ph, 4, 4)

        x += self._pw + 12
        if not self._data:
            return
        if self._type == "tv":
            title, year, type_str = (
                self._data.get("name", tr("unknown", "Unknown")),
                self._data.get("first_air_date", "")[:4],
                tr("tv_series", "TV Series"),
            )
        elif self._type == "movie":
            title, year, type_str = (
                self._data.get("title", tr("unknown", "Unknown")),
                self._data.get("release_date", "")[:4],
                tr("movie", "Movie"),
            )
        elif self._type == "album":
            title, year, type_str = (
                self._data.get("title", tr("unknown", "Unknown")),
                self._data.get("release_date", "")[:4],
                tr("album", "Album"),
            )
        else:
            title, year, type_str = (
                self._data.get("title")
                or self._data.get("name", tr("unknown", "Unknown")),
                "",
                tr("artist", "Artist"),
            )

        p.setPen(parse_color(c["green"]))
        p.setFont(QFont(Theme.FONT, 13, QFont.Weight.Bold))
        p.drawText(
            QRect(x, 8, self.width() - x - 12, 22), Qt.AlignmentFlag.AlignVCenter, title
        )
        subtitle = f"{year} · {type_str}" if year else type_str
        p.setPen(parse_color(c["secondary"]))
        p.setFont(QFont(Theme.FONT, 11))
        p.drawText(
            QRect(x, 30, self.width() - x - 12, 20),
            Qt.AlignmentFlag.AlignVCenter,
            subtitle,
        )
