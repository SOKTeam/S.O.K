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
Loading of posters and covers in the background, for the media pages.
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, Slot, QObject
from PySide6.QtGui import QPixmap

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
