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
"""Application-wide constants and configuration keys.

Defines service identifiers, configuration keys, environment variable names,
and other constants used throughout the S.O.K application.
"""

from __future__ import annotations

from cryptography.fernet import Fernet

SERVICE_TMDB = "tmdb"
SERVICE_TVDB = "tvdb"
SERVICE_OMDB = "omdb"
SERVICE_LASTFM = "lastfm"
SERVICE_SPOTIFY = "spotify"
SERVICE_DEEZER = "deezer"
SERVICE_MUSICBRAINZ = "musicbrainz"
SERVICE_GOOGLE_BOOKS = "google_books"
SERVICE_OPENLIBRARY = "openlibrary"
SERVICE_IGDB = "igdb"
SERVICE_RAWG = "rawg"
SERVICE_FANART = "fanart"
SERVICE_DISCORD = "discord"

CONFIG_KEY_TMDB = "api_key_tmdb_v4"
CONFIG_KEY_TVDB = "api_key_tvdb"
CONFIG_KEY_OMDB = "api_key_omdb"
CONFIG_KEY_LASTFM = "api_key_lastfm"
CONFIG_KEY_SPOTIFY_ID = "spotify_client_id"
CONFIG_KEY_SPOTIFY_SECRET = "spotify_client_secret"
CONFIG_KEY_GOOGLE_BOOKS = "google_books_api_key"
CONFIG_KEY_IGDB_ID = "igdb_client_id"
CONFIG_KEY_IGDB_SECRET = "igdb_client_secret"
CONFIG_KEY_RAWG = "api_key_rawg"
CONFIG_KEY_FANART = "api_key_fanart"
CONFIG_KEY_DISCORD = "client_id_discord"

ENV_TMDB = "API_KEY_TMDB_V4"
ENV_TVDB = "API_KEY_TVDB"
ENV_OMDB = "API_KEY_OMDB"
ENV_LASTFM = "API_KEY_LASTFM"
ENV_SPOTIFY_ID = "SPOTIFY_CLIENT_ID"
ENV_SPOTIFY_SECRET = "SPOTIFY_CLIENT_SECRET"
ENV_GOOGLE_BOOKS = "GOOGLE_BOOKS_API_KEY"
ENV_IGDB_ID = "IGDB_CLIENT_ID"
ENV_IGDB_SECRET = "IGDB_CLIENT_SECRET"
ENV_RAWG = "API_KEY_RAWG"
ENV_FANART = "API_KEY_FANART"
ENV_DISCORD = "CLIENT_ID_DISCORD"

API_KEY_CONFIG = {
    SERVICE_TMDB: CONFIG_KEY_TMDB,
    SERVICE_TVDB: CONFIG_KEY_TVDB,
    SERVICE_OMDB: CONFIG_KEY_OMDB,
    SERVICE_LASTFM: CONFIG_KEY_LASTFM,
    SERVICE_SPOTIFY: CONFIG_KEY_SPOTIFY_ID,
    SERVICE_GOOGLE_BOOKS: CONFIG_KEY_GOOGLE_BOOKS,
    SERVICE_IGDB: CONFIG_KEY_IGDB_ID,
    SERVICE_RAWG: CONFIG_KEY_RAWG,
    SERVICE_FANART: CONFIG_KEY_FANART,
    SERVICE_DISCORD: CONFIG_KEY_DISCORD,
}

API_KEY_ENV = {
    SERVICE_TMDB: ENV_TMDB,
    SERVICE_TVDB: ENV_TVDB,
    SERVICE_OMDB: ENV_OMDB,
    SERVICE_LASTFM: ENV_LASTFM,
    SERVICE_SPOTIFY: ENV_SPOTIFY_ID,
    SERVICE_GOOGLE_BOOKS: ENV_GOOGLE_BOOKS,
    SERVICE_IGDB: ENV_IGDB_ID,
    SERVICE_RAWG: ENV_RAWG,
    SERVICE_FANART: ENV_FANART,
    SERVICE_DISCORD: ENV_DISCORD,
}

API_SECRET_CONFIG = {
    SERVICE_SPOTIFY: CONFIG_KEY_SPOTIFY_SECRET,
    SERVICE_IGDB: CONFIG_KEY_IGDB_SECRET,
}

API_SECRET_ENV = {
    SERVICE_SPOTIFY: ENV_SPOTIFY_SECRET,
    SERVICE_IGDB: ENV_IGDB_SECRET,
}

FREE_SERVICES = [SERVICE_DEEZER, SERVICE_MUSICBRAINZ, SERVICE_OPENLIBRARY]
SERVICES_WITH_DEFAULT_KEYS = [SERVICE_TMDB, SERVICE_TVDB, SERVICE_FANART]
OAUTH_SERVICES = [SERVICE_LASTFM, SERVICE_SPOTIFY, SERVICE_IGDB]


class Constants:
    """Secure API keys injected at compile time."""

    _K: bytes = b""

    API_KEY_TMDB_V4 = ""
    API_KEY_TVDB = ""
    API_KEY_OMDB = ""
    API_KEY_LASTFM = ""
    API_KEY_RAWG = ""
    API_KEY_FANART = ""

    SPOTIFY_CLIENT_ID = ""
    SPOTIFY_CLIENT_SECRET = ""

    GOOGLE_BOOKS_API_KEY = ""

    IGDB_CLIENT_ID = ""
    IGDB_CLIENT_SECRET = ""

    CLIENT_ID_DISCORD = ""

    DEFAULT_LANGUAGE = ""
    DEFAULT_THEME = ""
    ENABLE_DISCORD_RPC = ""
    CHECK_UPDATES = ""

    @classmethod
    def get(cls, attr: str) -> str | None:
        """Retrieves and decrypts a constant value."""
        val = getattr(cls, attr, None)
        if val and attr != "_K":
            return Fernet(cls._K).decrypt(val.encode()).decode()
        return None

    @classmethod
    def has(cls, attr: str) -> bool:
        """Checks if a constant exists and is not empty."""
        return bool(getattr(cls, attr, None)) and attr != "_K"
