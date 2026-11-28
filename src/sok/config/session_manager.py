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
"""
Session Manager - Centralized management of sessions and API keys.

This module provides utilities for retrieving sessions
and API keys from configuration.
"""

import os
import ast
import logging
import time
from typing import Optional, Dict, Any

import requests

from sok.config.config_manager import ConfigManager
from sok.core.constants import (
    SERVICE_TMDB,
    SERVICE_TVDB,
    SERVICE_OMDB,
    SERVICE_LASTFM,
    SERVICE_SPOTIFY,
    SERVICE_IGDB,
    SERVICE_RAWG,
    SERVICE_FANART,
    API_KEY_CONFIG,
    API_KEY_ENV,
)
from sok.config.api_registry import get_service

logger = logging.getLogger(__name__)

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
# A token asked again an hour before it expires.
TOKEN_MARGIN_SECONDS = 3600
# The IGDB token of this process: {"client_id", "token", "expires"}.
_igdb_token: Dict[str, Any] = {}


def get_session_data(
    config: ConfigManager, service_id: str
) -> Optional[Dict[str, Any]]:
    """Extract session data for a service from the config.

    Works for all services (tmdb, lastfm, tvdb, etc.).

    Args:
        config: ConfigManager instance.
        service_id: Service identifier (tmdb, tvdb, lastfm, etc.).

    Returns:
        Dictionary containing session data or None if not found.
    """
    try:
        service_config = get_service(service_id)
        if service_config:
            session_key = service_config.session_key or f"{service_id}_session"
        else:
            session_key = f"{service_id}_session"
    except ImportError:
        session_key = f"{service_id}_session"

    session = config.get(session_key, "")
    if not session:
        return None

    if isinstance(session, dict):
        return session
    elif isinstance(session, str):
        if session.startswith("{"):
            try:
                return ast.literal_eval(session)
            except (ValueError, SyntaxError):
                pass
    return None


def get_api_key(config: ConfigManager, service_id: str) -> str:
    """Retrieve the API key for a service from config or environment.

    Args:
        config: ConfigManager instance.
        service_id: Service identifier.

    Returns:
        API key string or empty string if not found.
    """
    try:
        service_config = get_service(service_id)
        if service_config:
            key = (
                config.get(service_config.config_key, "")
                if service_config.config_key
                else ""
            )
            if not key and service_config.env_var:
                key = os.getenv(service_config.env_var, "")
            return key
    except ImportError:
        pass

    # Fallback for known services
    fallback = {
        SERVICE_TMDB: (API_KEY_CONFIG[SERVICE_TMDB], API_KEY_ENV[SERVICE_TMDB]),
        SERVICE_TVDB: (API_KEY_CONFIG[SERVICE_TVDB], API_KEY_ENV[SERVICE_TVDB]),
        SERVICE_OMDB: (API_KEY_CONFIG[SERVICE_OMDB], API_KEY_ENV[SERVICE_OMDB]),
        SERVICE_LASTFM: (API_KEY_CONFIG[SERVICE_LASTFM], API_KEY_ENV[SERVICE_LASTFM]),
        SERVICE_SPOTIFY: (
            API_KEY_CONFIG[SERVICE_SPOTIFY],
            API_KEY_ENV[SERVICE_SPOTIFY],
        ),
        SERVICE_IGDB: (API_KEY_CONFIG[SERVICE_IGDB], API_KEY_ENV[SERVICE_IGDB]),
        SERVICE_RAWG: (API_KEY_CONFIG[SERVICE_RAWG], API_KEY_ENV[SERVICE_RAWG]),
        SERVICE_FANART: (API_KEY_CONFIG[SERVICE_FANART], API_KEY_ENV[SERVICE_FANART]),
    }
    if service_id in fallback:
        config_key, env_var = fallback[service_id]
        return config.get(config_key, "") or os.getenv(env_var, "")
    return ""


def get_tmdb_session_id(config: ConfigManager) -> Optional[str]:
    """Extract the TMDB session_id from the config.

    Args:
        config: ConfigManager instance.

    Returns:
        TMDB session ID string or None if not found.
    """
    session_data = get_session_data(config, SERVICE_TMDB)
    if session_data:
        return session_data.get("session_id")
    return None


def get_tvdb_token(config: ConfigManager) -> Optional[str]:
    """Extract the TVDB token from the config.

    Args:
        config: ConfigManager instance.

    Returns:
        TVDB token string or None if not found.
    """
    session_data = get_session_data(config, SERVICE_TVDB)
    if session_data:
        return session_data.get("token")
    return None


def get_spotify_token(config: ConfigManager) -> Optional[str]:
    """Extract the Spotify token from the config.

    Args:
        config: ConfigManager instance.

    Returns:
        Spotify access token string or None if not found.
    """
    session_data = get_session_data(config, SERVICE_SPOTIFY)
    if session_data:
        return session_data.get("access_token")
    return None


def get_igdb_token(config: ConfigManager, renew: bool = False) -> Optional[str]:
    """The Twitch token that IGDB asks for, made from the client ID and secret.

    The token is asked from Twitch (client credentials) the first time, kept
    in memory until an hour before it expires (about 60 days), and asked
    again when ``renew`` is set (IGDB refused it). Nothing is saved: the
    server and the desktop app each ask for their own.

    Args:
        config: ConfigManager instance.
        renew: Ask for a new token even if the one kept is still valid.

    Returns:
        IGDB access token string, or None without the client ID and secret
        or when Twitch does not answer.
    """
    client_id = config.get("igdb_client_id", "")
    secret = config.get("igdb_client_secret", "")
    if not client_id or not secret:
        session_data = get_session_data(config, SERVICE_IGDB)
        return session_data.get("access_token") if session_data else None

    kept = _igdb_token
    if (
        not renew
        and kept.get("client_id") == client_id
        and kept.get("expires", 0) - TOKEN_MARGIN_SECONDS > time.time()
    ):
        return kept["token"]

    try:
        response = requests.post(
            TWITCH_TOKEN_URL,
            params={
                "client_id": client_id,
                "client_secret": secret,
                "grant_type": "client_credentials",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        token = data["access_token"]
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("No IGDB token from Twitch: %s", exc)
        return None
    _igdb_token.clear()
    _igdb_token.update(
        client_id=client_id,
        token=token,
        expires=time.time() + float(data.get("expires_in") or 0),
    )
    return token
