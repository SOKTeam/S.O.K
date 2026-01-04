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
"""Universal media manager for coordinating API access.

Provides a unified interface to search and retrieve media metadata from
multiple API sources (TMDB, Spotify, IGDB, etc.) based on media type.
"""

from typing import Dict, List, Any
import logging
import asyncio
from .interfaces import MediaAPI, MediaType, ContentType
from sok.core.constants import (
    SERVICE_TMDB,
    SERVICE_TVDB,
    SERVICE_OMDB,
    SERVICE_LASTFM,
    SERVICE_SPOTIFY,
    SERVICE_IGDB,
    SERVICE_DEEZER,
    SERVICE_MUSICBRAINZ,
    SERVICE_GOOGLE_BOOKS,
    SERVICE_OPENLIBRARY,
    SERVICE_RAWG,
    SERVICE_FANART,
)
from .exceptions import (
    APINotFoundError,
    UnsupportedMediaTypeError,
    APIError,
    APIConnectionError,
    APITimeoutError,
    APIResponseError,
)
from sok.core.adapters.media_adapters import adapt_search_results, adapt_details
from sok.config.config_manager import get_config_manager
from sok.config.session_manager import (
    get_api_key,
    get_tmdb_session_id,
    get_tvdb_token,
    get_igdb_token,
)
from sok.config.api_registry import get_services_by_media_type, APIGroup
from sok.apis.video.tmdb_api import TMDBApi
from sok.apis.video.tvdb_api import TVDBApi
from sok.apis.video.imdb_api import IMDBApi
from sok.apis.music.lastfm_api import LastFMApi
from sok.apis.music.deezer_api import DeezerApi
from sok.apis.music.spotify_api import SpotifyApi
from sok.apis.music.musicbrainz_api import MusicBrainzApi
from sok.apis.books.google_books_api import GoogleBooksApi
from sok.apis.books.open_library_api import OpenLibraryApi
from sok.apis.games.rawg_api import RAWGApi
from sok.apis.games.igdb_api import IGDBApi
from sok.apis.images.fanart_api import FanartApi

logger = logging.getLogger(__name__)

# Singleton instance
_manager_instance: "UniversalMediaManager | None" = None


def get_media_manager() -> "UniversalMediaManager":
    """
    Get the singleton instance of UniversalMediaManager.

    Returns:
        UniversalMediaManager: The shared manager instance.
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = UniversalMediaManager()
    return _manager_instance


def reset_media_manager() -> None:
    """Reset the singleton (useful for testing)."""
    global _manager_instance
    _manager_instance = None


class UniversalMediaManager:
    """Universal manager for all media types and APIs.

    Provides a unified interface to interact with multiple media APIs
    (TMDB, TVDB, Spotify, etc.) for searching and retrieving details
    about movies, TV shows, music, books, and games.

    Attributes:
        apis: Dictionary mapping API names to their instances.
        current_apis: Dictionary mapping media types to their currently selected API.

    Example:
        >>> manager = get_media_manager()
        >>> results = await manager.search("Breaking Bad", ContentType.TV_SERIES)
        >>> details = await manager.get_details("1396", ContentType.TV_SERIES)
    """

    def __init__(self, load_defaults: bool = True):
        """Initialize the media manager.

        Args:
            load_defaults: If True, automatically loads and registers
                all available APIs based on configuration.
        """
        self.apis: Dict[str, MediaAPI] = {}
        self.current_apis: Dict[MediaType, str] = {}
        if load_defaults:
            self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default configuration and register available APIs.

        Reads API keys from configuration and environment variables,
        then instantiates and registers all available API clients.
        Sets the preferred API for each media type based on user preferences.

        Raises:
            No exceptions are raised; errors are logged and skipped.
        """
        try:
            config = get_config_manager()

            api_classes = {
                SERVICE_TMDB: TMDBApi,
                SERVICE_TVDB: TVDBApi,
                SERVICE_OMDB: IMDBApi,
                SERVICE_LASTFM: LastFMApi,
                SERVICE_DEEZER: DeezerApi,
                SERVICE_SPOTIFY: SpotifyApi,
                SERVICE_MUSICBRAINZ: MusicBrainzApi,
                SERVICE_GOOGLE_BOOKS: GoogleBooksApi,
                SERVICE_OPENLIBRARY: OpenLibraryApi,
                SERVICE_RAWG: RAWGApi,
                SERVICE_IGDB: IGDBApi,
                SERVICE_FANART: FanartApi,
            }

            media_types = {
                "video": MediaType.VIDEO,
                "music": MediaType.MUSIC,
                "books": MediaType.BOOK,
                "games": MediaType.GAME,
            }

            for reg_type, media_type_enum in media_types.items():
                pref_key = f"preferred_api_{reg_type}"
                preferred_id = config.get(pref_key, "")
                services = get_services_by_media_type(reg_type)
                registered_ids = []

                for service in services:
                    if service.id not in api_classes:
                        logger.debug(
                            "API '%s' ignored: no associated class", service.id
                        )
                        continue

                    api_class = api_classes[service.id]
                    api_instance = None

                    try:
                        if service.group == APIGroup.FREE:
                            api_instance = api_class()
                        else:
                            if service.id == SERVICE_TMDB:
                                key = get_api_key(config, SERVICE_TMDB)
                                if key:
                                    session = get_tmdb_session_id(config)
                                    api_instance = api_class(key, session)
                            elif service.id == SERVICE_TVDB:
                                key = get_api_key(config, SERVICE_TVDB)
                                if key:
                                    token = get_tvdb_token(config)
                                    api_instance = api_class(key, token)
                            elif service.id == SERVICE_SPOTIFY:
                                client_id = config.get("spotify_client_id", "")
                                client_secret = config.get("spotify_client_secret", "")
                                if client_id and client_secret:
                                    api_instance = api_class(client_id, client_secret)
                            elif service.id == SERVICE_IGDB:
                                client_id = config.get("igdb_client_id", "")
                                access_token = get_igdb_token(config)
                                if client_id and access_token:
                                    api_instance = api_class(client_id, access_token)
                            else:
                                key = get_api_key(config, service.id)
                                if key:
                                    api_instance = api_class(key)

                        if api_instance:
                            self.register_api(service.id, api_instance)
                            registered_ids.append(service.id)
                        else:
                            logger.warning(
                                "API '%s' not initialized (missing configuration)",
                                service.id,
                            )
                    except (ImportError, ValueError, TypeError) as exc:
                        logger.warning(
                            "API '%s' initialization failed: %s",
                            service.id,
                            exc,
                            exc_info=exc,
                        )

                if preferred_id and preferred_id in registered_ids:
                    try:
                        self.set_current_api_for_media_type(
                            media_type_enum, preferred_id
                        )
                    except (APINotFoundError, UnsupportedMediaTypeError) as exc:
                        logger.warning(
                            "Unable to set preferred API '%s' for %s: %s",
                            preferred_id,
                            media_type_enum.value,
                            exc,
                            exc_info=exc,
                        )
                elif registered_ids:
                    try:
                        self.set_current_api_for_media_type(
                            media_type_enum, registered_ids[0]
                        )
                    except (APINotFoundError, UnsupportedMediaTypeError) as exc:
                        logger.warning(
                            "Unable to set default API '%s' for %s: %s",
                            registered_ids[0],
                            media_type_enum.value,
                            exc,
                            exc_info=exc,
                        )
                else:
                    logger.info("No API registered for type '%s'", reg_type)
        except ImportError as exc:
            logger.debug("API loading skipped (import error): %s", exc)

    def register_api(self, name: str, api_instance: MediaAPI) -> None:
        """Register a new API instance.

        Args:
            name: Unique identifier for the API (e.g., 'tmdb', 'spotify').
            api_instance: The API client instance implementing MediaAPI.
        """
        self.apis[name] = api_instance

    def set_current_api_for_media_type(
        self, media_type: MediaType, api_name: str
    ) -> None:
        """Set the current API for a media type.

        Args:
            media_type: The media type (VIDEO, MUSIC, BOOK, GAME).
            api_name: Name of the registered API to use.

        Raises:
            APINotFoundError: If the API is not registered.
            UnsupportedMediaTypeError: If the API doesn't support the media type.
        """
        if api_name not in self.apis:
            raise APINotFoundError(f"API '{api_name}' not found")

        if media_type not in self.apis[api_name].supported_media_types:
            raise UnsupportedMediaTypeError(
                f"API '{api_name}' does not support type '{media_type.value}'"
            )

        self.current_apis[media_type] = api_name

    def get_available_apis_for_media_type(self, media_type: MediaType) -> List[str]:
        """Return available APIs for a media type.

        Args:
            media_type: The media type to query.

        Returns:
            List of API names that support the given media type.
        """
        return [
            name
            for name, api in self.apis.items()
            if media_type in api.supported_media_types
        ]

    def get_current_api(self, media_type: MediaType) -> MediaAPI:
        """Return the current API for a media type.

        Args:
            media_type: The media type to get the API for.

        Returns:
            The currently selected API instance for the media type.

        Raises:
            UnsupportedMediaTypeError: If no API is available for the media type.
        """
        if media_type not in self.current_apis:
            available_apis = self.get_available_apis_for_media_type(media_type)
            if not available_apis:
                raise UnsupportedMediaTypeError(
                    f"No API available for type '{media_type.value}'"
                )
            self.current_apis[media_type] = available_apis[0]

        return self.apis[self.current_apis[media_type]]

    async def search(
        self, query: str, content_type: ContentType, **kwargs: Any
    ) -> Dict[str, Any]:
        """Search for media using the appropriate API.

        Args:
            query: Search query string.
            content_type: Type of content to search for.
            **kwargs: Additional API-specific parameters (e.g., language, year).

        Returns:
            Dict containing 'results' key with list of matching items.

        Raises:
            APITimeoutError: If the request times out.
            APIConnectionError: If connection to API fails.
            APIResponseError: If API returns invalid response.
            APIError: For any other API-related errors.
        """
        media_type = self._get_media_type_from_content_type(content_type)
        api = self.get_current_api(media_type)
        api_name = self.current_apis.get(media_type, "unknown")
        try:
            raw = await api.search(query, content_type, **kwargs)
            results = raw.get("results", []) if isinstance(raw, dict) else []
            return adapt_search_results(content_type, results)
        except asyncio.TimeoutError as exc:
            logger.error(
                "Timeout during search via API '%s': %s", api_name, exc, exc_info=exc
            )
            raise APITimeoutError(
                f"Timeout during search via API '{api_name}'", api_name
            ) from exc
        except (ConnectionError, OSError) as exc:
            logger.error("API '%s' connection error: %s", api_name, exc, exc_info=exc)
            raise APIConnectionError(
                f"API '{api_name}' connection error: {exc}", api_name
            ) from exc
        except (KeyError, ValueError, TypeError) as exc:
            logger.error(
                "API '%s' response parsing error: %s", api_name, exc, exc_info=exc
            )
            raise APIResponseError(
                f"Invalid response from API '{api_name}': {exc}", api_name
            ) from exc
        except Exception as exc:  # noqa: BLE001 - last resort to avoid app crash
            logger.exception(
                "Unexpected error during search via API '%s': %s", api_name, exc
            )
            raise APIError(
                f"Search failed via API '{api_name}': {exc}", api_name
            ) from exc

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs: Any
    ) -> Dict[str, Any]:
        """Get detailed information about a media item.

        Args:
            item_id: Unique identifier of the item.
            content_type: Type of content.
            **kwargs: Additional parameters (e.g., language, append_to_response).

        Returns:
            Dict containing detailed information about the item.

        Raises:
            APITimeoutError: If the request times out.
            APIConnectionError: If connection to API fails.
            APIResponseError: If API returns invalid response.
            APIError: For any other API-related errors.
        """
        media_type = self._get_media_type_from_content_type(content_type)
        api = self.get_current_api(media_type)
        api_name = self.current_apis.get(media_type, "unknown")
        try:
            raw = await api.get_details(item_id, content_type, **kwargs)
            return adapt_details(content_type, raw)
        except asyncio.TimeoutError as exc:
            logger.error(
                "Timeout fetching details via API '%s': %s", api_name, exc, exc_info=exc
            )
            raise APITimeoutError(
                f"Timeout fetching details via API '{api_name}'", api_name
            ) from exc
        except (ConnectionError, OSError) as exc:
            logger.error("API '%s' connection error: %s", api_name, exc, exc_info=exc)
            raise APIConnectionError(
                f"API '{api_name}' connection error: {exc}", api_name
            ) from exc
        except (KeyError, ValueError, TypeError) as exc:
            logger.error(
                "API '%s' response parsing error: %s", api_name, exc, exc_info=exc
            )
            raise APIResponseError(
                f"Invalid response from API '{api_name}': {exc}", api_name
            ) from exc
        except APIError:
            raise
        except Exception as exc:  # noqa: BLE001 - last resort to avoid app crash
            logger.exception(
                "Unexpected error fetching details via API '%s': %s", api_name, exc
            )
            raise APIError(
                f"Details fetch failed via API '{api_name}': {exc}", api_name
            ) from exc

    def _get_media_type_from_content_type(self, content_type: ContentType) -> MediaType:
        """Determine media type from content type.

        Args:
            content_type: The specific content type.

        Returns:
            The corresponding media type category.
        """
        mapping = {
            ContentType.MOVIE: MediaType.VIDEO,
            ContentType.TV_SERIES: MediaType.VIDEO,
            ContentType.EPISODE: MediaType.VIDEO,
            ContentType.DOCUMENTARY: MediaType.VIDEO,
            ContentType.ALBUM: MediaType.MUSIC,
            ContentType.TRACK: MediaType.MUSIC,
            ContentType.ARTIST: MediaType.MUSIC,
            ContentType.PLAYLIST: MediaType.MUSIC,
            ContentType.BOOK: MediaType.BOOK,
            ContentType.AUDIOBOOK: MediaType.BOOK,
            ContentType.EBOOK: MediaType.BOOK,
            ContentType.COMIC: MediaType.BOOK,
            ContentType.GAME: MediaType.GAME,
            ContentType.DLC: MediaType.GAME,
        }
        return mapping[content_type]
