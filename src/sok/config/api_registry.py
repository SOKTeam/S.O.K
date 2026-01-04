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
API Registry - Centralized configuration of API services

This file centralizes all API configurations to facilitate
adding new services in the future.

To add a new API:
1. Add an entry in API_SERVICES
2. Create the authentication class in oauth_providers.py (if OAuth required)
3. Create the API class in the appropriate apis/ folder
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum


class AuthType(Enum):
    """Authentication type required by the API.

    Attributes:
        API_KEY: Simple API key authentication.
        OAUTH: OAuth 2.0 flow authentication.
        BEARER: Bearer token authentication.
        SESSION: Session-based authentication.
    """

    API_KEY = "api_key"
    OAUTH = "oauth"
    BEARER = "bearer"
    SESSION = "session"


class APIGroup(Enum):
    """API constraint group for categorization.

    Attributes:
        FREE: No API key required.
        API_KEY: API key required.
        AUTH: Account and login required.
        RESTRICTIVE: Limited or restrictive access.
    """

    FREE = "free"
    API_KEY = "api_key"
    AUTH = "auth"
    RESTRICTIVE = "restrictive"


@dataclass
class APIServiceConfig:
    """API service configuration dataclass.

    Attributes:
        id: Unique service identifier.
        name: Display name of the service.
        description: Brief description of the service.
        media_type: Type of media handled (video, music, etc.).
        auth_type: Authentication type required.
        group: API constraint group.
        config_key: Key for storing API credentials in config.
        session_key: Key for session storage.
        api_key_url: URL to obtain API key.
        base_url: Base URL for API requests.
        env_var: Environment variable name.
        requires_secret: Whether a client secret is required.
        secret_config_key: Key for storing client secret.
        icon: Icon identifier for UI.
        enabled: Whether the service is enabled.
    """

    id: str
    name: str
    description: str
    media_type: str
    auth_type: AuthType
    group: APIGroup
    config_key: str

    session_key: str = ""

    api_key_url: str = ""

    base_url: str = ""

    env_var: str = ""

    requires_secret: bool = False
    secret_config_key: str = ""
    icon: str = ""
    enabled: bool = True


API_SERVICES: Dict[str, APIServiceConfig] = {
    "tmdb": APIServiceConfig(
        id="tmdb",
        name="TMDB",
        description="Movie and TV series metadata",
        media_type="video",
        auth_type=AuthType.API_KEY,
        group=APIGroup.API_KEY,
        config_key="api_key_tmdb_v4",
        session_key="",
        api_key_url="https://www.themoviedb.org/settings/api",
        base_url="https://api.themoviedb.org/3/",
        env_var="API_KEY_TMDB_V4",
        icon="",
    ),
    "tvdb": APIServiceConfig(
        id="tvdb",
        name="TVDB",
        description="TV series metadata",
        media_type="video",
        auth_type=AuthType.API_KEY,
        group=APIGroup.API_KEY,
        config_key="api_key_tvdb",
        session_key="",
        api_key_url="https://thetvdb.com/api-information",
        base_url="https://api4.thetvdb.com/v4/",
        env_var="API_KEY_TVDB",
        icon="",
    ),
    "omdb": APIServiceConfig(
        id="omdb",
        name="OMDb",
        description="Open Movie Database (IMDb)",
        media_type="video",
        auth_type=AuthType.API_KEY,
        group=APIGroup.RESTRICTIVE,
        config_key="api_key_omdb",
        api_key_url="https://www.omdbapi.com/apikey.aspx",
        base_url="https://www.omdbapi.com/",
        env_var="API_KEY_OMDB",
        icon="",
    ),
    "lastfm": APIServiceConfig(
        id="lastfm",
        name="Last.fm",
        description="Music metadata and scrobbling",
        media_type="music",
        auth_type=AuthType.OAUTH,
        group=APIGroup.API_KEY,
        config_key="api_key_lastfm",
        session_key="lastfm_session",
        api_key_url="https://www.last.fm/api/account/create",
        base_url="https://ws.audioscrobbler.com/2.0/",
        env_var="API_KEY_LASTFM",
        requires_secret=True,
        secret_config_key="api_secret_lastfm",
        icon="",
    ),
    "spotify": APIServiceConfig(
        id="spotify",
        name="Spotify",
        description="Spotify music metadata",
        media_type="music",
        auth_type=AuthType.OAUTH,
        group=APIGroup.AUTH,
        config_key="spotify_client_id",
        session_key="spotify_session",
        api_key_url="https://developer.spotify.com/dashboard",
        base_url="https://api.spotify.com/v1/",
        env_var="SPOTIFY_CLIENT_ID",
        requires_secret=True,
        secret_config_key="spotify_client_secret",
        icon="",
    ),
    "deezer": APIServiceConfig(
        id="deezer",
        name="Deezer",
        description="Music metadata (free)",
        media_type="music",
        auth_type=AuthType.API_KEY,
        group=APIGroup.FREE,
        config_key="",
        api_key_url="",
        base_url="https://api.deezer.com/",
        env_var="",
        icon="",
    ),
    "musicbrainz": APIServiceConfig(
        id="musicbrainz",
        name="MusicBrainz",
        description="Open music database",
        media_type="music",
        auth_type=AuthType.API_KEY,
        group=APIGroup.FREE,
        config_key="",
        api_key_url="",
        base_url="https://musicbrainz.org/ws/2/",
        env_var="",
        icon="",
    ),
    "google_books": APIServiceConfig(
        id="google_books",
        name="Google Books",
        description="Google Books metadata",
        media_type="books",
        auth_type=AuthType.API_KEY,
        group=APIGroup.FREE,
        config_key="google_books_api_key",
        api_key_url="https://console.cloud.google.com/apis/credentials",
        base_url="https://www.googleapis.com/books/v1/",
        env_var="GOOGLE_BOOKS_API_KEY",
        icon="",
    ),
    "openlibrary": APIServiceConfig(
        id="openlibrary",
        name="Open Library",
        description="Open library (free)",
        media_type="books",
        auth_type=AuthType.API_KEY,
        group=APIGroup.FREE,
        config_key="",
        api_key_url="",
        base_url="https://openlibrary.org/",
        env_var="",
        icon="",
    ),
    "igdb": APIServiceConfig(
        id="igdb",
        name="IGDB",
        description="Game metadata (via Twitch)",
        media_type="games",
        auth_type=AuthType.OAUTH,
        group=APIGroup.AUTH,
        config_key="igdb_client_id",
        session_key="igdb_session",
        api_key_url="https://dev.twitch.tv/console/apps",
        base_url="https://api.igdb.com/v4/",
        env_var="IGDB_CLIENT_ID",
        requires_secret=True,
        secret_config_key="igdb_client_secret",
        icon="",
    ),
    "rawg": APIServiceConfig(
        id="rawg",
        name="RAWG",
        description="Video game database",
        media_type="games",
        auth_type=AuthType.API_KEY,
        group=APIGroup.FREE,
        config_key="api_key_rawg",
        api_key_url="https://rawg.io/apidocs",
        base_url="https://api.rawg.io/api/",
        env_var="API_KEY_RAWG",
        icon="",
    ),
    "fanart": APIServiceConfig(
        id="fanart",
        name="Fanart.tv",
        description="High quality artwork",
        media_type="images",
        auth_type=AuthType.API_KEY,
        group=APIGroup.API_KEY,
        config_key="api_key_fanart",
        api_key_url="https://fanart.tv/get-an-api-key/",
        base_url="https://webservice.fanart.tv/v3/",
        env_var="API_KEY_FANART",
        icon="",
    ),
}

GROUP_ORDER = [APIGroup.FREE, APIGroup.API_KEY, APIGroup.AUTH, APIGroup.RESTRICTIVE]

GROUP_LABELS = {
    APIGroup.FREE: ("api_group_free", "Free (No key required)"),
    APIGroup.API_KEY: ("api_group_api_key", "API Key Required"),
    APIGroup.AUTH: ("api_group_auth", "Account & Login Required"),
    APIGroup.RESTRICTIVE: ("api_group_restrictive", "Restrictive / Limited"),
}

CATEGORY_ORDER = ["video", "music", "books", "games", "images", "other"]

CATEGORY_LABELS = {
    "video": ("category_video", "Video (Movies & Series)"),
    "music": ("category_music", "Music"),
    "books": ("category_books", "Books"),
    "games": ("category_games", "Video Games"),
    "images": ("category_images", "Artwork & Images"),
    "other": ("category_other", "Other services"),
}


def get_service(service_id: str) -> Optional[APIServiceConfig]:
    """Retrieve a service configuration by its ID.

    Args:
        service_id: Unique identifier of the service.

    Returns:
        Service configuration if found, None otherwise.
    """
    return API_SERVICES.get(service_id)


def get_services_by_media_type(media_type: str) -> List[APIServiceConfig]:
    """Retrieve all services for a media type.

    Args:
        media_type: Type of media (video, music, books, games).

    Returns:
        List of enabled services for the specified media type.
    """
    return [
        s for s in API_SERVICES.values() if s.media_type == media_type and s.enabled
    ]


def get_enabled_services() -> List[APIServiceConfig]:
    """Retrieve all enabled services.

    Returns:
        List of all enabled API service configurations.
    """
    return [s for s in API_SERVICES.values() if s.enabled]


def get_oauth_services() -> List[APIServiceConfig]:
    """Retrieve all services requiring OAuth or Session authentication.

    Returns:
        List of services using OAuth, Session, or Bearer auth.
    """
    return [
        s
        for s in API_SERVICES.values()
        if s.enabled
        and s.auth_type in (AuthType.OAUTH, AuthType.SESSION, AuthType.BEARER)
    ]


def get_services_by_category() -> Dict[str, List[APIServiceConfig]]:
    """Retrieve all services grouped by category.

    Returns:
        Dictionary with categories as keys and list of services as values.
        Order is defined by CATEGORY_ORDER.
    """
    result = {}
    for category in CATEGORY_ORDER:
        services = [
            s for s in API_SERVICES.values() if s.media_type == category and s.enabled
        ]
        if services:
            result[category] = services
    return result


def get_all_services() -> List[APIServiceConfig]:
    """Retrieve all enabled services.

    Returns:
        List of all enabled API service configurations.
    """
    return [s for s in API_SERVICES.values() if s.enabled]


def get_all_config_keys() -> Dict[str, str]:
    """Return a service_id to config_key mapping for all services.

    Returns:
        Dictionary mapping service IDs to their config keys.
    """
    return {s.id: s.config_key for s in API_SERVICES.values() if s.config_key}


def get_all_env_vars() -> Dict[str, str]:
    """Return a config_key to env_var mapping for .env loading.

    Returns:
        Dictionary mapping config keys to environment variable names.
    """
    result = {}
    for service in API_SERVICES.values():
        if service.config_key and service.env_var:
            result[service.config_key] = service.env_var
        if service.requires_secret and service.secret_config_key:
            secret_env = service.env_var.replace("_ID", "_SECRET").replace(
                "_KEY", "_SECRET"
            )
            if not secret_env.endswith("_SECRET"):
                secret_env = service.env_var + "_SECRET"
            result[service.secret_config_key] = secret_env
    return result
