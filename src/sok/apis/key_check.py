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
"""Check that the key of a service works, with one light request.

The API clients do not all report a wrong key (some log it and return no
result), so each service has its own probe here: a request that needs the
key and nothing else, read by its status and, for OMDb and Last.fm, by its
body. No Qt; the server uses it for the "Test" button of its settings.
"""

import asyncio
import base64
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, FrozenSet, Optional, Tuple

import aiohttp

# The result of a check (KeyCheck.status).
OK = "ok"
WRONG_KEY = "wrong_key"
MISSING_KEY = "missing_key"
RATE_LIMITED = "rate_limited"
SERVICE_ERROR = "service_error"
UNREACHABLE = "unreachable"
UNSUPPORTED = "unsupported"

TIMEOUT_SECONDS = 10

# fetch(method, url, params, headers, data, json) -> (status, body)
Fetch = Callable[..., Awaitable[Tuple[int, Any]]]


@dataclass
class KeyCheck:
    """What a check found; detail is the message of the service, if any."""

    service: str
    status: str
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == OK


@dataclass
class Probe:
    """The request that checks the key of one service."""

    method: str
    url: str
    # Builds (params, headers, data, json) from the key and the secret.
    build: Callable[[str, str], Tuple[Dict, Dict, Any, Any]]
    needs_secret: bool = False
    # Statuses that mean a wrong key, besides 401 and 403.
    wrong_statuses: FrozenSet[int] = field(default_factory=frozenset)
    # Reads a 2xx or error body that hides the result (OMDb, Last.fm).
    read_body: Optional[Callable[[Any], Optional[str]]] = None


def _bearer(key: str, _secret: str) -> Tuple[Dict, Dict, Any, Any]:
    return {}, {"Authorization": f"Bearer {key}"}, None, None


def _param(
    name: str, **extra: str
) -> Callable[[str, str], Tuple[Dict, Dict, Any, Any]]:
    def build(key: str, _secret: str) -> Tuple[Dict, Dict, Any, Any]:
        return {name: key, **extra}, {}, None, None

    return build


def _spotify(key: str, secret: str) -> Tuple[Dict, Dict, Any, Any]:
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    return (
        {},
        {"Authorization": f"Basic {auth}"},
        {"grant_type": "client_credentials"},
        None,
    )


def _twitch(key: str, secret: str) -> Tuple[Dict, Dict, Any, Any]:
    params = {
        "client_id": key,
        "client_secret": secret,
        "grant_type": "client_credentials",
    }
    return params, {}, None, None


def _omdb_body(body: Any) -> Optional[str]:
    """OMDb answers a wrong key or a used quota with an "Error"."""
    if isinstance(body, dict) and body.get("Response") == "False":
        error = str(body.get("Error", ""))
        if "limit" in error.lower():
            return RATE_LIMITED
        if "key" in error.lower():
            return WRONG_KEY
    return None


def _lastfm_body(body: Any) -> Optional[str]:
    """Last.fm gives an error number: 10 and 26 for the key, 29 for the rate."""
    if isinstance(body, dict) and "error" in body:
        return RATE_LIMITED if body["error"] == 29 else WRONG_KEY
    return None


PROBES: Dict[str, Probe] = {
    "tmdb": Probe("GET", "https://api.themoviedb.org/3/authentication", _bearer),
    "tvdb": Probe(
        "POST",
        "https://api4.thetvdb.com/v4/login",
        lambda key, _s: ({}, {}, None, {"apikey": key}),
    ),
    "omdb": Probe(
        "GET",
        "https://www.omdbapi.com/",
        _param("apikey", i="tt0111161"),
        read_body=_omdb_body,
    ),
    "lastfm": Probe(
        "GET",
        "https://ws.audioscrobbler.com/2.0/",
        _param("api_key", method="artist.getinfo", artist="Daft Punk", format="json"),
        read_body=_lastfm_body,
    ),
    "spotify": Probe(
        "POST",
        "https://accounts.spotify.com/api/token",
        _spotify,
        needs_secret=True,
        wrong_statuses=frozenset({400}),
    ),
    "google_books": Probe(
        "GET",
        "https://www.googleapis.com/books/v1/volumes",
        _param("key", q="dune", maxResults="1"),
        wrong_statuses=frozenset({400}),
    ),
    "igdb": Probe(
        "POST",
        "https://id.twitch.tv/oauth2/token",
        _twitch,
        needs_secret=True,
        wrong_statuses=frozenset({400}),
    ),
    "rawg": Probe("GET", "https://api.rawg.io/api/games", _param("key", page_size="1")),
    # A movie without images answers 404: the key was accepted.
    "fanart": Probe(
        "GET", "https://webservice.fanart.tv/v3/movies/603", _param("api_key")
    ),
}


async def _fetch(
    method: str,
    url: str,
    params: Dict,
    headers: Dict,
    data: Any,
    json: Any,
) -> Tuple[int, Any]:
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.request(
            method, url, params=params, headers=headers, data=data, json=json
        ) as response:
            try:
                body = await response.json(content_type=None)
            except ValueError:
                body = None
            return response.status, body


def _detail(body: Any) -> str:
    if not isinstance(body, dict):
        return ""
    error = body.get("error")
    if isinstance(error, dict):
        error = error.get("message")
    for value in (
        body.get("status_message"),
        body.get("message"),
        body.get("Error"),
        body.get("error_description"),
        error,
    ):
        if value and isinstance(value, str):
            return value[:200]
    return ""


async def check_key(
    service: str, key: str, secret: str = "", fetch: Fetch = _fetch
) -> KeyCheck:
    """Check the key (and secret) of a service with one request.

    Args:
        service: The id of the service, as in the API registry.
        key: The key, or the client id for Spotify and IGDB.
        secret: The client secret of Spotify and IGDB.
        fetch: Makes the request; tests give a fake one.
    """
    probe = PROBES.get(service)
    if probe is None:
        return KeyCheck(service, UNSUPPORTED)
    if not key or (probe.needs_secret and not secret):
        return KeyCheck(service, MISSING_KEY)

    params, headers, data, json = probe.build(key, secret)
    try:
        status, body = await fetch(probe.method, probe.url, params, headers, data, json)
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
        return KeyCheck(service, UNREACHABLE, str(exc)[:200])

    detail = _detail(body)
    from_body = probe.read_body(body) if probe.read_body else None
    if from_body:
        return KeyCheck(service, from_body, detail)
    if status in (401, 403) or status in probe.wrong_statuses:
        return KeyCheck(service, WRONG_KEY, detail)
    if status == 429:
        return KeyCheck(service, RATE_LIMITED, detail)
    if status < 400 or (service == "fanart" and status == 404):
        return KeyCheck(service, OK)
    return KeyCheck(service, SERVICE_ERROR, detail or f"HTTP {status}")
