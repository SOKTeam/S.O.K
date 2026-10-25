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

import aiohttp
import pytest

from sok.apis.key_check import (
    MISSING_KEY,
    OK,
    PROBES,
    RATE_LIMITED,
    SERVICE_ERROR,
    UNREACHABLE,
    UNSUPPORTED,
    WRONG_KEY,
    check_key,
)
from sok.config.api_registry import get_all_services


def answer(status, body=None):
    """A fake fetch that answers status and body, and keeps the request."""
    calls = []

    async def fetch(method, url, params, headers, data, json):
        calls.append(
            {"method": method, "url": url, "params": params, "headers": headers}
        )
        return status, body

    fetch.calls = calls
    return fetch


def check(service, fetch, key="the-key", secret="the-secret"):
    return asyncio.run(check_key(service, key, secret, fetch=fetch))


def test_every_service_with_a_key_has_a_probe():
    for service in get_all_services():
        if service.config_key:
            assert service.id in PROBES, service.id


@pytest.mark.parametrize("service", sorted(PROBES))
def test_an_accepted_key_is_ok(service):
    assert check(service, answer(200, {})).status == OK


@pytest.mark.parametrize("service", sorted(PROBES))
def test_401_and_403_are_a_wrong_key(service):
    assert check(service, answer(401, {})).status == WRONG_KEY
    assert check(service, answer(403, {})).status == WRONG_KEY


def test_the_tmdb_key_is_a_bearer_token():
    fetch = answer(200, {"success": True})

    check("tmdb", fetch)

    assert fetch.calls[0]["headers"] == {"Authorization": "Bearer the-key"}


def test_spotify_and_igdb_need_their_secret():
    assert check("spotify", answer(200), secret="").status == MISSING_KEY
    assert check("igdb", answer(200), secret="").status == MISSING_KEY
    assert check("spotify", answer(400, {"error": "invalid_client"})).status == (
        WRONG_KEY
    )


def test_omdb_and_lastfm_are_read_by_their_body():
    assert (
        check("omdb", answer(200, {"Response": "False", "Error": "Invalid API key!"}))
    ).status == WRONG_KEY
    assert (
        check(
            "omdb",
            answer(401, {"Response": "False", "Error": "Request limit reached!"}),
        )
    ).status == RATE_LIMITED
    assert check("lastfm", answer(200, {"error": 10})).status == WRONG_KEY
    assert check("lastfm", answer(200, {"error": 29})).status == RATE_LIMITED


def test_a_fanart_movie_without_images_means_the_key_works():
    assert check("fanart", answer(404, {"status": "error"})).status == OK


def test_other_answers():
    assert check("tmdb", answer(429, {})).status == RATE_LIMITED
    result = check("tmdb", answer(503, {"status_message": "Down"}))
    assert (result.status, result.detail) == (SERVICE_ERROR, "Down")
    assert check("deezer", answer(200)).status == UNSUPPORTED
    assert check("tmdb", answer(200), key="").status == MISSING_KEY


def test_no_network():
    async def fetch(*args):
        raise aiohttp.ClientConnectionError("no route to host")

    assert check("tmdb", fetch).status == UNREACHABLE
