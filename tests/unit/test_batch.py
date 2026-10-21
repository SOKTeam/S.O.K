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
import asyncio
from pathlib import Path

import pytest

from sok.core.batch import (
    STATUS_AMBIGUOUS,
    STATUS_MISSING,
    STATUS_READY,
    BatchMatcher,
    ParsedName,
    author_matches,
    evaluate,
    normalize_title,
    parse_book,
    parse_movie,
    same_book,
)
from sok.core.exceptions import APIConnectionError
from sok.core.interfaces import ContentType


def movie(title, date, original=None):
    return {"title": title, "original_title": original or title, "release_date": date}


DUNE_RESULTS = [
    movie("Dune : Troisième partie", "2026-12-16", "Dune: Part Three"),
    movie("Dune", "2021-09-15"),
    movie("Dune", "1984-12-14"),
]


def test_titles_are_compared_without_accents_case_or_punctuation():
    assert normalize_title("Dune: Part Two") == normalize_title("dune.part.two")
    assert normalize_title("Amélie") == normalize_title("AMELIE")
    assert normalize_title("Fast & Furious") == normalize_title("Fast and Furious")


def test_title_and_year_match_is_ready():
    assert evaluate("Dune", 2021, DUNE_RESULTS) == (1, STATUS_READY)


def test_first_result_with_another_title_is_not_ready():
    # The case that renamed Dune (2021) as "Dune : Troisième partie (2026)".
    selected, status = evaluate("Dune", 2021, DUNE_RESULTS)
    assert selected != 0
    assert status == STATUS_READY


def test_same_title_without_year_is_to_pick():
    assert evaluate("Dune", None, DUNE_RESULTS) == (1, STATUS_AMBIGUOUS)


def test_unique_title_without_year_is_ready():
    results = [
        movie("Inception", "2010-07-16"),
        movie("Inception: The Cobol Job", "2010"),
    ]
    assert evaluate("Inception", None, results) == (0, STATUS_READY)


def test_original_title_matches_a_translated_result():
    results = [movie("Dune : Deuxième partie", "2024-02-28", "Dune: Part Two")]
    assert evaluate("Dune Part Two", 2024, results) == (0, STATUS_READY)


def test_year_alone_selects_but_is_to_pick():
    results = [movie("Heat", "1986-03-14"), movie("Révélations", "1995-12-15")]
    assert evaluate("Heat", 1995, results) == (1, STATUS_AMBIGUOUS)


def test_two_exact_matches_are_to_pick():
    results = [movie("Dune", "2021-09-15"), movie("Dune", "2021-10-22")]
    assert evaluate("Dune", 2021, results) == (0, STATUS_AMBIGUOUS)


def test_nothing_found_is_missing():
    assert evaluate("Dune", 2021, []) == (None, STATUS_MISSING)


def test_movie_query_and_year_come_from_the_file_name():
    assert parse_movie([Path("Dune.Part.Two.2024.2160p.mkv")]) == ParsedName(
        "Dune Part Two", 2024
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("blade.runner.2049.2017.mkv", ("Blade Runner 2049", 2017)),
        ("Blade Runner 2049 (2017).mkv", ("Blade Runner 2049", 2017)),
        ("1917.2019.1080p.mkv", ("1917", 2019)),
        ("Movie.2010.1920x1080.mkv", ("Movie", 2010)),
    ],
)
def test_a_number_of_the_title_is_not_the_year(name, expected):
    parsed = parse_movie([Path(name)])

    assert (parsed.query.title(), parsed.year) == expected


class FakeManager:
    def __init__(self, results=None, error=None):
        self.results = results or {}
        self.error = error
        self.calls = []

    async def search(self, query, content_type, **kwargs):
        self.calls.append((query, content_type, kwargs))
        if self.error:
            raise self.error
        return {"results": self.results.get(query, [])}


def test_matcher_searches_every_file_in_order():
    manager = FakeManager({"Dune": DUNE_RESULTS, "Heat": [movie("Heat", "1995-12-15")]})
    matcher = BatchMatcher(manager, ContentType.MOVIE, parse_movie, "fr-FR")
    progress = []

    matches = asyncio.run(
        matcher.match_all(
            [[Path("Dune.2021.mkv")], [Path("Heat (1995).mkv")]],
            lambda done, total, file: progress.append((done, total)),
        )
    )

    assert [(m.file.name, m.status, m.selected) for m in matches] == [
        ("Dune.2021.mkv", STATUS_READY, 1),
        ("Heat (1995).mkv", STATUS_READY, 0),
    ]
    assert sorted(progress) == [(1, 2), (2, 2)]
    assert manager.calls[0] == ("Dune", ContentType.MOVIE, {"language": "fr-FR"})


def test_typed_query_keeps_the_year_of_the_file():
    manager = FakeManager({"Dune 2021": [], "Dune": DUNE_RESULTS})
    matcher = BatchMatcher(manager, ContentType.MOVIE, parse_movie)

    match = asyncio.run(matcher.match([Path("Dune.2021.mkv")], "Dune"))

    assert (match.query, match.year, match.status) == ("Dune", 2021, STATUS_READY)
    assert manager.calls == [("Dune", ContentType.MOVIE, {})]


def test_failed_search_is_missing():
    manager = FakeManager(error=APIConnectionError("offline"))
    matcher = BatchMatcher(manager, ContentType.MOVIE, parse_movie)

    match = asyncio.run(matcher.match([Path("Dune.2021.mkv")]))

    assert (match.candidates, match.selected, match.status) == (
        [],
        None,
        STATUS_MISSING,
    )


def book(title, authors, date):
    return {"title": title, "authors": authors, "published_date": date}


HERBERT = ["Frank Herbert"]


def test_editions_of_one_book_are_ready():
    results = [book("Dune", HERBERT, "1965"), book("Dune", HERBERT, "2005")]
    assert evaluate("Dune", None, results, "Frank Herbert", same_book) == (
        0,
        STATUS_READY,
    )


def test_books_by_other_authors_are_to_pick():
    results = [book("Dune", HERBERT, "1965"), book("Dune", ["Someone Else"], "2010")]
    assert evaluate("Dune", None, results, None, same_book) == (0, STATUS_AMBIGUOUS)


def test_the_author_of_the_file_name_picks_the_book():
    results = [book("Dune", ["Someone Else"], "2010"), book("Dune", HERBERT, "1965")]
    assert evaluate("Dune", None, results, "Herbert", same_book) == (1, STATUS_READY)


def test_movies_with_one_title_and_year_stay_to_pick():
    # Without same_work, two results are two works, even with one title.
    results = [movie("Arrival", "2016-11-10"), movie("Arrival", "2016-05-25")]
    assert evaluate("Arrival", 2016, results) == (0, STATUS_AMBIGUOUS)


def test_an_author_matches_by_full_or_last_name():
    candidate = book("Dune", ["Frank Herbert", "Brian Herbert"], "1965")
    assert author_matches("Frank Herbert", candidate)
    assert author_matches("herbert", candidate)
    assert not author_matches("Asimov", candidate)


def test_book_file_name_gives_title_and_author_but_no_year():
    parsed = parse_book(
        [Path("Ursula K. Le Guin - The Left Hand of Darkness (1969).epub")]
    )
    assert parsed == ParsedName(
        "The Left Hand of Darkness Ursula K. Le Guin",
        None,
        "The Left Hand of Darkness",
        "Ursula K. Le Guin",
    )


def test_book_matcher_compares_the_title_not_the_whole_query():
    manager = FakeManager({"Dune Frank Herbert": [book("Dune", HERBERT, "1965")]})
    matcher = BatchMatcher(manager, ContentType.BOOK, parse_book, None, same_book)

    match = asyncio.run(matcher.match([Path("Frank Herbert - Dune.epub")]))

    assert (match.query, match.status, match.selected) == (
        "Dune Frank Herbert",
        STATUS_READY,
        0,
    )
