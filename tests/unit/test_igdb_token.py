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
"""The Twitch token of IGDB: asked when needed, kept, asked again."""

import asyncio

import pytest
import requests

from sok.apis.games.igdb_api import IGDBApi
from sok.config import session_manager
from sok.core.exceptions import APIAuthenticationError
from sok.core.interfaces import ContentType


class FakeConfig:
    def __init__(self, **values):
        self.values = values

    def get(self, key, default=None):
        return self.values.get(key, default)


class Answer:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"HTTP {self.status}")

    def json(self):
        return self.data


@pytest.fixture
def twitch(monkeypatch):
    """Twitch answering a new token at each call; the calls are kept."""
    calls = []

    def post(url, params, timeout):
        calls.append(params)
        return Answer({"access_token": f"token-{len(calls)}", "expires_in": 5000000})

    session_manager._igdb_token.clear()
    monkeypatch.setattr(session_manager.requests, "post", post)
    yield calls
    session_manager._igdb_token.clear()


KEYS = FakeConfig(igdb_client_id="id", igdb_client_secret="secret")


def test_the_token_is_asked_once_then_kept(twitch):
    assert session_manager.get_igdb_token(KEYS) == "token-1"
    assert session_manager.get_igdb_token(KEYS) == "token-1"
    assert twitch == [
        {
            "client_id": "id",
            "client_secret": "secret",
            "grant_type": "client_credentials",
        }
    ]


def test_renew_asks_a_new_token(twitch):
    session_manager.get_igdb_token(KEYS)

    assert session_manager.get_igdb_token(KEYS, renew=True) == "token-2"
    assert session_manager.get_igdb_token(KEYS) == "token-2"


def test_a_token_close_to_its_end_is_asked_again(twitch, monkeypatch):
    session_manager.get_igdb_token(KEYS)
    session_manager._igdb_token["expires"] = session_manager.time.time() + 60

    assert session_manager.get_igdb_token(KEYS) == "token-2"


def test_other_keys_get_their_own_token(twitch):
    session_manager.get_igdb_token(KEYS)
    other = FakeConfig(igdb_client_id="other", igdb_client_secret="secret")

    assert session_manager.get_igdb_token(other) == "token-2"


def test_no_token_without_the_secret(twitch):
    assert session_manager.get_igdb_token(FakeConfig(igdb_client_id="id")) is None
    assert twitch == []


def test_no_token_when_twitch_refuses_the_keys(monkeypatch):
    session_manager._igdb_token.clear()
    monkeypatch.setattr(
        session_manager.requests,
        "post",
        lambda url, params, timeout: Answer({"message": "invalid client"}, 400),
    )

    assert session_manager.get_igdb_token(KEYS) is None


def test_an_expired_token_is_renewed_and_the_search_made_again():
    api = IGDBApi("id", "old", renew=lambda: "new")
    tokens = []

    async def fake_request(endpoint, headers, method, data):
        tokens.append(headers["Authorization"])
        if headers["Authorization"] == "Bearer old":
            raise APIAuthenticationError("HTTP 401", "IGDB")
        return [{"id": 1, "name": "Super Mario World"}]

    api._make_request = fake_request
    found = asyncio.run(api.search("Super Mario World", ContentType.GAME))

    assert tokens == ["Bearer old", "Bearer new"]
    assert found["results"][0]["title"] == "Super Mario World"


def test_a_refused_token_without_a_new_one_stays_an_error():
    api = IGDBApi("id", "old", renew=lambda: None)

    async def fake_request(endpoint, headers, method, data):
        raise APIAuthenticationError("HTTP 401", "IGDB")

    api._make_request = fake_request
    with pytest.raises(APIAuthenticationError):
        asyncio.run(api.search("Super Mario World", ContentType.GAME))
