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
from pathlib import Path

import pytest
import requests

from sok.file_operations import artwork
from sok.file_operations.artwork import (
    artwork_targets,
    download_artwork,
    image_url,
    save_artwork,
)
from sok.media.books.book import Book
from sok.media.games.game import Game
from sok.media.music.album import Album
from sok.media.music.track import Track
from sok.media.video.movie import Movie
from sok.media.video.series import Series
from sok.media.factory import create_media_item


def with_poster(item, url="https://img/x.jpg"):
    item.poster_url = url
    return item


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/abc.jpg", "https://image.tmdb.org/t/p/original/abc.jpg"),
        ("https://cdn/x.jpg", "https://cdn/x.jpg"),
        ("//cdn/x.jpg", "https://cdn/x.jpg"),
        ("", None),
        (None, None),
    ],
)
def test_image_url(path, expected):
    assert image_url(path) == expected


def test_a_movie_poster_goes_next_to_the_file(tmp_path):
    movie = with_poster(Movie("Dune", "en", None))

    targets = artwork_targets(movie, [str(tmp_path / "Dune (2021).mkv")], str(tmp_path))

    assert targets == {tmp_path / "Dune (2021)-poster.jpg": "https://img/x.jpg"}


def test_a_series_poster_goes_in_the_series_folder(tmp_path):
    series = with_poster(Series("Severance", "en", None), "/sev.jpg")
    moved = [str(tmp_path / "Severance" / "Season 1" / "Severance S01E01.mkv")]

    targets = artwork_targets(series, moved, str(tmp_path))

    assert targets == {
        tmp_path / "Severance" / "poster.jpg": (
            "https://image.tmdb.org/t/p/original/sev.jpg"
        )
    }


def test_an_album_cover_goes_in_the_album_folder(tmp_path):
    album = with_poster(Album("Discovery", "Daft Punk", 2001))
    folder = tmp_path / "Daft Punk - Discovery"
    moved = [
        str(folder / "01 - One More Time.mp3"),
        str(folder / "02 - Aerodynamic.mp3"),
    ]

    assert artwork_targets(album, moved, str(tmp_path)) == {
        folder / "cover.jpg": "https://img/x.jpg"
    }


def test_no_cover_in_a_folder_shared_by_several_albums(tmp_path):
    track = with_poster(Track("Get Lucky", "en", None, "Daft Punk", "Random Access"))
    moved = [str(tmp_path / "Daft Punk" / "Get Lucky.mp3")]

    assert artwork_targets(track, moved, str(tmp_path)) == {}


def test_a_book_cover_goes_in_the_book_folder(tmp_path):
    book = with_poster(Book("Dune", "en", None), "https://covers/1-L.png")
    folder = tmp_path / "Frank Herbert" / "Frank Herbert - Dune (1965)"

    targets = artwork_targets(book, [str(folder / "Dune.epub")], str(tmp_path))

    assert targets == {folder / "cover.png": "https://covers/1-L.png"}


def test_games_and_items_without_image_get_nothing(tmp_path):
    moved = [str(tmp_path / "Halo.iso")]
    assert artwork_targets(with_poster(Game("Halo", "en", None)), moved, "") == {}
    assert artwork_targets(Movie("Dune", "en", None), moved, "") == {}


class FakeResponse:
    def __init__(self, content_type="image/jpeg", status=200):
        self.headers = {"Content-Type": content_type}
        self.content = b"jpeg"
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"HTTP {self.status}")


def test_download_saves_and_keeps_existing_images(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        artwork.requests,
        "get",
        lambda url, timeout: calls.append(url) or FakeResponse(),
    )
    existing = tmp_path / "poster.jpg"
    existing.write_bytes(b"mine")
    new = tmp_path / "cover.jpg"

    report = download_artwork({existing: "https://a", new: "https://b"})

    assert existing.read_bytes() == b"mine"
    assert new.read_bytes() == b"jpeg"
    assert calls == ["https://b"]
    assert report["saved"] == [str(new)] and report["kept"] == [str(existing)]


@pytest.mark.parametrize(
    "response",
    [FakeResponse("text/html"), FakeResponse(status=404)],
)
def test_a_failed_download_leaves_nothing(tmp_path, monkeypatch, response):
    monkeypatch.setattr(artwork.requests, "get", lambda url, timeout: response)
    target = tmp_path / "cover.jpg"

    report = download_artwork({target: "https://b"})

    assert list(tmp_path.iterdir()) == []
    assert report["errors"][0]["file"] == str(target)


def test_save_artwork_uses_the_moved_files_only(tmp_path, monkeypatch):
    saved = {}
    monkeypatch.setattr(
        artwork, "download_artwork", lambda targets: saved.update(targets)
    )
    dune = with_poster(Movie("Dune", "en", None))
    heat = with_poster(Movie("Heat", "en", None), "https://img/heat.jpg")
    mappings = [(Path("/in/dune.mkv"), dune), (Path("/in/heat.mkv"), heat)]
    moved = [{"from": "/in/dune.mkv", "to": str(tmp_path / "Dune (2021).mkv")}]

    save_artwork(mappings, moved, str(tmp_path))

    assert saved == {tmp_path / "Dune (2021)-poster.jpg": "https://img/x.jpg"}


def test_the_factory_keeps_the_poster_of_a_result():
    item = create_media_item(
        {"id": 1, "title": "Dune", "poster_path": "/dune.jpg"}, "movie", None
    )
    book = create_media_item(
        {"id": 2, "title": "Dune", "image_url": "https://covers/2-L.jpg"}, "book", None
    )

    assert item.poster_url == "/dune.jpg"
    assert book.poster_url == "https://covers/2-L.jpg"
