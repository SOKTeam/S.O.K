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
import pytest

from sok.core.exceptions import (
    APIAuthenticationError,
    APIConnectionError,
    APIError,
    APINotFoundError,
    APIRateLimitError,
    APIResponseError,
    APITimeoutError,
)
from sok.ui.errors import error_message, service_name
from sok.ui.i18n import tr


@pytest.mark.parametrize(
    "api_name, expected",
    [
        ("google_books", "Google Books"),
        ("GoogleBooks", "Google Books"),
        ("LastFM", "Last.fm"),
        ("IMDB", "OMDb"),
        ("RAWG", "RAWG"),
        ("SomethingNew", "SomethingNew"),
    ],
)
def test_service_name_comes_from_the_registry(api_name, expected):
    assert service_name(api_name) == expected


def test_an_unknown_service_gets_a_generic_name():
    assert service_name("unknown") == tr("error_online_service", "The online service")


@pytest.mark.parametrize(
    "error, key",
    [
        (APIAuthenticationError("HTTP 401", "RAWG"), "error_api_key"),
        (APIRateLimitError("HTTP 429", "GoogleBooks"), "error_api_quota"),
        (APITimeoutError("timeout", "TMDB"), "error_api_timeout"),
        (APIConnectionError("down", "TMDB"), "error_api_connection"),
        (APINotFoundError("HTTP 404", "TMDB"), "error_api_not_found"),
        (APIResponseError("HTTP 502", "TMDB"), "error_api_response"),
        (APIError("odd", "TMDB"), "error_api_response"),
    ],
)
def test_each_api_error_has_its_message(error, key):
    message = error_message(error)

    template = tr(key, "")
    assert message.startswith(template.split("{")[0])
    assert "HTTP" not in message


def test_the_message_names_the_service_and_where_to_fix_the_key():
    message = error_message(APIAuthenticationError("HTTP 401", "RAWG"))

    assert "RAWG" in message
    assert tr("api_keys", "API Keys") in message


def test_a_rate_limit_with_retry_after_says_when():
    message = error_message(APIRateLimitError("HTTP 429", "TMDB", retry_after=30))

    assert "30" in message


def test_other_errors_keep_their_text():
    assert error_message(RuntimeError("No API configured for video.")) == (
        "No API configured for video."
    )
