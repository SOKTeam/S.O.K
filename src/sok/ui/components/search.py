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
from PySide6.QtCore import Qt, Signal, Slot, QObject, QRect
from PySide6.QtGui import QPainter, QFont, QPixmap, QPainterPath

from sok.ui.theme import Theme
from sok.ui.components.base import parse_color
from sok.ui.i18n import tr
import logging
import urllib.error
import urllib.request
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

import shiboken6

logger = logging.getLogger(__name__)


_CACHE_SIZE = 200

# GUI-thread state: downloaded bytes by URL, downloads in flight, and the
# widgets waiting for each of them.
_cache: OrderedDict[str, bytes] = OrderedDict()
_pending: dict[str, Future] = {}
_waiters: dict[str, list[tuple[object, QWidget, Callable, tuple[int, int]]]] = {}


class _PosterDelivery(QObject):
    """Hands downloaded poster bytes back to the GUI thread.

    It lives in the GUI thread, so ready, emitted from a pool thread,
    is queued to _on_ready there.
    """

    ready = Signal(str, bytes)

    def __init__(self):
        """Initialize the delivery object and connect its own slot."""
        super().__init__()
        self.ready.connect(self._on_ready)

    @Slot(str, bytes)
    def _on_ready(self, url: str, data: bytes):
        """Cache a finished download and pass it to the widgets waiting for it.

        Args:
            url: Image URL.
            data: Downloaded image bytes, empty if the download failed.
        """
        _pending.pop(url, None)
        if data:
            _cache[url] = data
            _cache.move_to_end(url)
            while len(_cache) > _CACHE_SIZE:
                _cache.popitem(last=False)
        for _, receiver, on_loaded, size in _waiters.pop(url, []):
            _deliver(receiver, on_loaded, data, size)


_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="poster")
_delivery: _PosterDelivery | None = None


def _download(url: str) -> bytes:
    """Download an image, or return empty bytes on failure.

    Args:
        url: Image URL.
    """
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        logger.debug("Poster download failed for %s: %s", url, exc)
        return b""


def _deliver(receiver: QWidget, on_loaded, data: bytes, size: tuple[int, int]):
    """Build the pixmap in the GUI thread and pass it to its widget.

    Args:
        receiver: Widget that asked for the image.
        on_loaded: Callback taking the scaled pixmap.
        data: Downloaded image bytes.
        size: Target (width, height).
    """
    # The row may have been deleted by a newer search meanwhile.
    if not data or not shiboken6.isValid(receiver):
        return
    pm = QPixmap()
    pm.loadFromData(data)
    if pm.isNull():
        return
    on_loaded(
        pm.scaled(
            *size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
    )


def _forget(url: str, token: object):
    """Drop a deleted widget's request; cancel the download if nobody waits.

    Args:
        url: Image URL.
        token: Identifies the request in _waiters.
    """
    waiters = [w for w in _waiters.get(url, []) if w[0] is not token]
    if waiters:
        _waiters[url] = waiters
        return
    _waiters.pop(url, None)
    future = _pending.get(url)
    # A download already running finishes and fills the cache.
    if future is not None and future.cancel():
        _pending.pop(url, None)


def load_poster(url: str, width: int, height: int, receiver: QWidget, on_loaded):
    """Download a poster in the background and hand it to a widget.

    The download runs in a shared thread pool, never in a QThread owned by
    the widget: deleting a widget whose QThread still runs aborts the app.
    QPixmap is only created in the GUI thread. Each URL is downloaded once:
    selecting a result reuses the image of its row.

    Args:
        url: Image URL.
        width: Target width.
        height: Target height.
        receiver: Widget showing the image; nothing happens once it is deleted.
        on_loaded: Callback taking the scaled pixmap.
    """
    global _delivery
    data = _cache.get(url)
    if data:
        _cache.move_to_end(url)
        _deliver(receiver, on_loaded, data, (width, height))
        return

    token = object()
    _waiters.setdefault(url, []).append((token, receiver, on_loaded, (width, height)))
    receiver.destroyed.connect(lambda *_: _forget(url, token))
    if url in _pending:
        return

    if _delivery is None:
        _delivery = _PosterDelivery()
    delivery = _delivery

    def _done(f: Future):
        if not f.cancelled():
            delivery.ready.emit(url, f.result())

    future = _pool.submit(_download, url)
    _pending[url] = future
    future.add_done_callback(_done)


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
            load_poster(url, self._pw, self._ph, self, self._on_poster_loaded)

    def _on_poster_loaded(self, pixmap):
        """Handle loaded poster image.

        Args:
            pixmap: Loaded image pixmap.
        """
        self._poster = pixmap
        self.update()

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
        title = (
            self._data.get("title")
            or self._data.get("name")
            or tr("unknown", "Unknown")
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
            year = (self._data.get("first_air_date") or "")[:4]
        elif self._type == "movie":
            year = (self._data.get("release_date") or "")[:4]
        elif self._type == "album":
            year = (self._data.get("release_date") or "")[:4]

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
        self._poster_url: str | None = None
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
        self._poster_url = None
        poster_path = data.get("poster_path")
        if poster_path:
            url = (
                poster_path
                if poster_path.startswith("http")
                else f"https://image.tmdb.org/t/p/w92{poster_path}"
            )
            self._poster_url = url
            load_poster(
                url,
                self._pw,
                self._ph,
                self,
                lambda pixmap, u=url: self._on_poster_loaded(pixmap, u),
            )
        self.update()

    def clear(self):
        """Clear the selected media."""
        self._data, self._type, self._poster, self._empty = None, None, None, True
        self._poster_url = None
        self.update()

    def _on_poster_loaded(self, pixmap, url: str):
        """Handle loaded poster image.

        Args:
            pixmap: Loaded image pixmap.
            url: URL it was loaded from; ignored if another media is shown now.
        """
        if url != self._poster_url:
            return
        self._poster = pixmap
        self.update()

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
                self._data.get("name") or tr("unknown", "Unknown"),
                (self._data.get("first_air_date") or "")[:4],
                tr("tv_series", "TV Series"),
            )
        elif self._type == "movie":
            title, year, type_str = (
                self._data.get("title") or tr("unknown", "Unknown"),
                (self._data.get("release_date") or "")[:4],
                tr("movie", "Movie"),
            )
        elif self._type == "album":
            title, year, type_str = (
                self._data.get("title") or tr("unknown", "Unknown"),
                (self._data.get("release_date") or "")[:4],
                tr("album", "Album"),
            )
        else:
            title, year, type_str = (
                self._data.get("title")
                or self._data.get("name")
                or tr("unknown", "Unknown"),
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
