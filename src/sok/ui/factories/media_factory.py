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
from sok.media.music.track import Track
from sok.media.books.book import Book
from sok.media.games.game import Game
from sok.core.media_manager import UniversalMediaManager

logger = logging.getLogger(__name__)

MediaItem = Union[Series, Movie, Album, Track, Book, Game]


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
    elif content_type == "track":
        track = Track(
            title,
            language,
            manager,
            artist=data.get("artist") or "",
            album=data.get("album") or "",
            track_number=0,
        )
        track.id = str(data.get("id"))
        number = str(data.get("track_number") or "")
        track.track_number = int(number) if number.isdigit() else 0
        release = str(data.get("release_date") or "")
        track.year = int(release[:4]) if release[:4].isdigit() else None
        item = track
    elif content_type == "book":
        book = Book(title, language, manager)
        book.id = str(data.get("id"))
        # Search results give a list of authors, details a single string.
        author = data.get("author") or ", ".join(data.get("authors") or [])
        if author:
            book.author = author
        if data.get("published_date"):
            book.published_date = str(data["published_date"])
        item = book
    elif content_type == "game":
        # The platform comes from the files (see GameFileOperations), not from
        # the many platforms a game is released on.
        game = Game(title, language, manager, platform="")
        game.id = str(data.get("id"))
        if data.get("release_date"):
            game.release_date = str(data["release_date"])
        item = game

    return item
