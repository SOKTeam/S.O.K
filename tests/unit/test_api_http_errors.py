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
import json

import aiohttp
import pytest

from sok.apis.books.google_books_api import GoogleBooksApi
from sok.apis.music.deezer_api import DeezerApi
from sok.core.exceptions import (
    APIAuthenticationError,
    APIConnectionError,
    APINotFoundError,
    APIRateLimitError,
    APIResponseError,
)


class FakeResponse:
    def __init__(self, status, body, headers=None):
        self.status = status
        self.headers = headers or {}
        self._body = body

    async def json(self, content_type="application/json"):
        if not isinstance(self._body, (dict, list)):
            if content_type is None:
                return json.loads(self._body)
            raise aiohttp.ContentTypeError(None, (), message="not JSON")
        return self._body

    async def text(self):
        return self._body if isinstance(self._body, str) else json.dumps(self._body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def get(self, url, params=None, headers=None):
        if self.error:
            raise self.error
        return self.response


def request(response=None, error=None):
    api = GoogleBooksApi()

    async def fake_session():
        return FakeSession(response, error)

    api._ensure_session = fake_session
    return asyncio.run(api._make_request("volumes", {"q": "Dune"}))


def test_a_success_returns_the_json():
    assert request(FakeResponse(200, {"items": []})) == {"items": []}


def test_an_exhausted_quota_is_a_rate_limit_error():
    google_429 = {"error": {"code": 429, "message": "Quota exceeded for quota metric"}}

    with pytest.raises(APIRateLimitError) as info:
        request(FakeResponse(429, google_429, {"Retry-After": "30"}))

    assert "Quota exceeded" in str(info.value)
    assert info.value.retry_after == 30
    assert info.value.api_name == "GoogleBooks"


@pytest.mark.parametrize("status", [401, 403])
def test_a_wrong_key_is_an_authentication_error(status):
    with pytest.raises(APIAuthenticationError, match="Invalid API key"):
        request(FakeResponse(status, {"status_message": "Invalid API key"}))


def test_not_found_is_a_not_found_error():
    with pytest.raises(APINotFoundError):
        request(FakeResponse(404, {"message": "Not found"}))


def test_a_server_error_is_a_response_error_even_without_json():
    with pytest.raises(APIResponseError, match="Bad Gateway"):
        request(FakeResponse(502, "<html>Bad Gateway</html>"))


def test_a_success_that_is_not_json_is_a_response_error():
    with pytest.raises(APIResponseError):
        request(FakeResponse(200, "<html>maintenance</html>"))


def test_a_network_failure_is_a_connection_error():
    with pytest.raises(APIConnectionError):
        request(error=aiohttp.ClientConnectionError("unreachable"))


def test_api_name_comes_from_the_class():
    assert GoogleBooksApi().api_name == "GoogleBooks"
    assert DeezerApi().api_name == "Deezer"
