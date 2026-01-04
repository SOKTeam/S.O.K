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
"""Helpers to build media domain objects from API payloads."""

from __future__ import annotations

import logging
from typing import Union
from sok.media.video.series import Series
from sok.media.video.movie import Movie
from sok.media.music.album import Album
from sok.media.books.book import Book
from sok.media.games.game import Game
from sok.core.media_manager import UniversalMediaManager

logger = logging.getLogger(__name__)

MediaItem = Union[Series, Movie, Album, Book, Game]


def create_media_item(
    data: dict, content_type: str, manager: UniversalMediaManager, language: str = "en"
) -> MediaItem | None:
    """Create domain media objects from API response data.

    Keeps UI code free of domain instantiation details.
    """
    if not data:
        return None

    title = data.get("title") or data.get("name", "Unknown")
    item: MediaItem | None = None

    if content_type == "tv":
        series = Series(title, language, manager)
        series.id = str(data.get("id"))
        if "episodes" in data:
            series.episodes = data["episodes"]
        item = series
    elif content_type == "movie":
        movie = Movie(title, language, manager)
        movie.id = str(data.get("id"))
        release = data.get("release_date", "")
        if release:
            try:
                movie.year = int(release.split("-")[0])
            except (ValueError, IndexError) as exc:
                logger.warning("Failed to extract year for %s: %s", title, exc)
        item = movie
    elif content_type in ("album", "artist"):
        artist = data.get("artist", "")
        if isinstance(artist, dict):
            artist = artist.get("name", "")
        year: int | None = None
        release_date = data.get("release_date", "")
        if release_date:
            try:
                year = int(str(release_date).split("-")[0])
            except (ValueError, IndexError):
                pass
        album = Album(title, artist, year)
        album.id = str(data.get("mbid") or data.get("url") or title)
        if "tracks" in data:
            album.tracks = data.get("tracks", {})
        item = album
    elif content_type == "book":
        book = Book(title, language, manager)
        book.id = str(data.get("id"))
        author = data.get("author", "")
        if author:
            book.author = author
        item = book
    elif content_type == "game":
        game = Game(title, language, manager)
        game.id = str(data.get("id"))
        item = game

    return item
