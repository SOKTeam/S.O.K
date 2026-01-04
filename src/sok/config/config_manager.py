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
Configuration Manager for S.O.K
"""

import json
import sys
import os
import threading
import logging
from cryptography.fernet import Fernet, InvalidToken
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from sok.core.constants import (
    Constants,
    SERVICE_TMDB,
    SERVICE_DEEZER,
    SERVICE_GOOGLE_BOOKS,
    SERVICE_IGDB,
)
from dotenv import load_dotenv
import ctypes

logger = logging.getLogger(__name__)

IS_COMPILED = "__compiled__" in globals()


def get_base_path() -> Path:
    """Get the base path for the application.

    Returns:
        Path to executable directory if compiled,
        or project root directory if running from source.
    """
    if IS_COMPILED:
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[3]


BASE_PATH = get_base_path()

try:
    HAS_SECURE_CONSTANTS = True
except ImportError:
    HAS_SECURE_CONSTANTS = False
    SERVICE_TMDB = "tmdb"
    SERVICE_DEEZER = "deezer"
    SERVICE_GOOGLE_BOOKS = "google_books"
    SERVICE_IGDB = "igdb"

    class Constants:  # type: ignore[no-redef]
        """Stub class when constants module is not available."""

        @classmethod
        def get(cls, attr: str) -> None:
            """Get a constant value.

            Args:
                attr: Attribute name.

            Returns:
                Always returns None in stub.
            """
            return None

        @classmethod
        def has(cls, attr: str) -> bool:
            """Check if constant exists.

            Args:
                attr: Attribute name.

            Returns:
                Always returns False in stub.
            """
            return False


if not HAS_SECURE_CONSTANTS:
    try:
        env_path = BASE_PATH / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass


def get_local_key() -> bytes:
    """Retrieve or generate an encryption key specific to this installation.

    The key is stored in data/.local.key and is hidden on Windows.
    If no key exists, a new one is generated using Fernet.

    Returns:
        The local encryption key as bytes.
    """
    key_file = BASE_PATH / "data" / ".local.key"
    if key_file.exists():
        return key_file.read_bytes()

    new_key = Fernet.generate_key()
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(new_key)
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetFileAttributesW(str(key_file), 2)
    return new_key


@dataclass
class AppConfig:
    """
    Application configuration data class.

    Attributes:
        language: UI language code
        theme: UI theme (dark or light)
        is_prod: Whether the app is running in production (compiled) mode
    """

    language: str = "en"
    theme: str = "dark"
    is_prod: bool = HAS_SECURE_CONSTANTS

    api_key_tmdb_v4: str = ""
    api_key_tvdb: str = ""
    api_key_omdb: str = ""

    api_key_lastfm: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    google_books_api_key: str = ""

    igdb_client_id: str = ""
    igdb_client_secret: str = ""
    api_key_rawg: str = ""

    api_key_fanart: str = ""

    client_id_discord: str = ""

    default_video_path: str = ""
    default_music_path: str = ""
    default_books_path: str = ""
    default_games_path: str = ""

    auto_organize: bool = False
    create_folders: bool = True
    download_posters: bool = False
    use_discord_rpc: bool = False
    check_updates: bool = True

    video_format: str = "{title} S{season}E{episode} {episode_title}"
    movie_format: str = "{title} ({year})"
    music_format: str = "{artist} - {album}/{track} - {title}"

    backup_before_rename: bool = True
    skip_duplicates: bool = True
    log_operations: bool = True

    preferred_api_video: str = SERVICE_TMDB
    preferred_api_music: str = SERVICE_DEEZER
    preferred_api_books: str = SERVICE_GOOGLE_BOOKS
    preferred_api_games: str = SERVICE_IGDB

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class ConfigManager:
    """Configuration manager for S.O.K application.

    Handles loading, saving, and accessing application configuration.
    Supports encrypted storage for sensitive fields (API keys) and
    runtime overrides from environment variables or constants.

    Attributes:
        config_path: Path to the configuration JSON file.
        config: Current AppConfig instance.
        fernet: Fernet instance for encryption/decryption.
        SENSITIVE_FIELDS: List of field names that are encrypted.

    Example:
        >>> config = get_config_manager()
        >>> theme = config.get('theme', 'dark')
        >>> config.set('language', 'en')
    """

    SENSITIVE_FIELDS = [
        "api_key_tmdb_v4",
        "api_key_tvdb",
        "api_key_omdb",
        "api_key_lastfm",
        "api_key_rawg",
        "spotify_client_id",
        "spotify_client_secret",
        "igdb_client_id",
        "igdb_client_secret",
    ]

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file
        """
        if config_path is None:
            config_path = BASE_PATH / "data" / "config.json"

        self.config_path = Path(config_path)
        self.config = AppConfig()
        self._runtime_values: Dict[str, Any] = {}
        self.fernet = Fernet(get_local_key())
        self.load()

    def load(self) -> None:
        """Load configuration from file, constants, or environment variables.

        Priority for values:
        1. User configuration file (config.json)
        2. Compile-time constants (in production builds)
        3. Environment variables (.env file)

        Sensitive fields are automatically decrypted if prefixed with 'ENC:'.
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    for field in self.SENSITIVE_FIELDS:
                        val = data.get(field, "")
                        if val.startswith("ENC:"):
                            try:
                                raw_val = val.replace("ENC:", "")
                                data[field] = self.fernet.decrypt(
                                    raw_val.encode()
                                ).decode()
                            except (InvalidToken, ValueError) as exc:
                                logger.exception(
                                    "Decryption failed for %s", field, exc_info=exc
                                )
                                data[field] = ""

                    self.config = AppConfig.from_dict(data)
            except (OSError, json.JSONDecodeError) as exc:
                logger.exception("Configuration loading failed", exc_info=exc)
                self.config = AppConfig()
        else:
            self.save()

        self.config.is_prod = HAS_SECURE_CONSTANTS

        def get_val(key):
            """Get configuration value from constants or environment.

            Args:
                key: Configuration key name.

            Returns:
                Value from constants if available, otherwise from environment.
            """
            if HAS_SECURE_CONSTANTS and hasattr(Constants, key):
                return Constants.get(key)
            return os.getenv(key)

        def get_bool(key):
            """Get boolean configuration value from constants or environment.

            Args:
                key: Configuration key name.

            Returns:
                Boolean value, or None if not found.
            """
            if HAS_SECURE_CONSTANTS and hasattr(Constants, key):
                val = Constants.get(key)
                if isinstance(val, bool):
                    return val
                return str(val).lower() in ("true", "1", "yes", "on")
            env_val = os.getenv(key)
            if env_val is not None:
                return env_val.lower() in ("true", "1", "yes", "on")
            return None

        env_mapping = {
            "api_key_tmdb_v4": "API_KEY_TMDB_V4",
            "api_key_tvdb": "API_KEY_TVDB",
            "api_key_lastfm": "API_KEY_LASTFM",
            "api_key_omdb": "API_KEY_OMDB",
            "spotify_client_id": "SPOTIFY_CLIENT_ID",
            "spotify_client_secret": "SPOTIFY_CLIENT_SECRET",
            "google_books_api_key": "GOOGLE_BOOKS_API_KEY",
            "igdb_client_id": "IGDB_CLIENT_ID",
            "igdb_client_secret": "IGDB_CLIENT_SECRET",
            "client_id_discord": "CLIENT_ID_DISCORD",
        }

        try:
            load_dotenv(BASE_PATH / ".env")
        except ImportError:
            pass

        if HAS_SECURE_CONSTANTS:
            for config_key, const_key in env_mapping.items():
                val = None
                if hasattr(Constants, const_key):
                    val = Constants.get(const_key)

                if not val:
                    val = os.getenv(env_mapping[config_key])

                if val:
                    self._runtime_values[config_key] = val
        else:
            for config_key, env_key in env_mapping.items():
                val = os.getenv(env_key)
                if val:
                    self._runtime_values[config_key] = val

        bool_env_mapping = {
            "use_discord_rpc": "ENABLE_DISCORD_RPC",
            "check_updates": "CHECK_UPDATES",
            "auto_organize": "AUTO_ORGANIZE",
            "create_folders": "CREATE_FOLDERS",
            "download_posters": "DOWNLOAD_POSTERS",
            "backup_before_rename": "BACKUP_BEFORE_RENAME",
            "skip_duplicates": "SKIP_DUPLICATES",
            "log_operations": "LOG_OPERATIONS",
        }

        for config_key, env_key in bool_env_mapping.items():
            val = get_bool(env_key)
            if val is not None:
                self._runtime_values[config_key] = val

        theme_val = get_val("DEFAULT_THEME")
        if theme_val and not self.config_path.exists():
            self.config.theme = theme_val

    def save(self) -> None:
        """Save configuration to file.

        Sensitive fields are automatically encrypted with 'ENC:' prefix
        before being written to the JSON file.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        data = self.config.to_dict()

        for field in self.SENSITIVE_FIELDS:
            if data.get(field):
                encrypted = self.fernet.encrypt(data[field].encode()).decode()
                data[field] = f"ENC:{encrypted}"

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except OSError as exc:
            logger.exception("Configuration saving failed", exc_info=exc)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value (Effective value).
        Priority: User Config > Runtime Overrides (Env/Constants)

        Args:
            key: Configuration key
            default: Default value if key doesn't exist

        Returns:
            Configuration value
        """
        val = getattr(self.config, key, None)
        if val not in (None, ""):
            return val

        if key in self._runtime_values:
            return self._runtime_values[key]

        return default

    def get_user_value(self, key: str, default: Any = None) -> Any:
        """
        Get value strictly from user configuration (no overrides).
        Used for UI display to avoid showing Dev keys.

        Args:
            key: Configuration key
            default: Default value

        Returns:
            User saved value
        """
        return getattr(self.config, key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: New value
        """
        if hasattr(self.config, key):
            setattr(self.config, key, value)
            self.save()

    def update(self, **kwargs: Any) -> None:
        """
        Update multiple configuration values.

        Args:
            **kwargs: Key-value pairs to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save()

    def reset(self) -> None:
        """Reset configuration to default values.

        Creates a new AppConfig with default values and saves it,
        effectively clearing all user customizations.
        """
        self.config = AppConfig()
        self.save()

    def _get_i18n_dir(self) -> Path:
        """Get the translations directory path.

        Returns:
            Path to the i18n directory containing language JSON files.
        """
        if IS_COMPILED:
            return Path(sys.executable).parent / "resources" / "i18n"
        return Path(__file__).resolve().parent.parent / "resources" / "i18n"

    def get_language_file(self) -> Path:
        """
        Get path to current language file.

        Returns:
            Path to language JSON file
        """
        return self._get_i18n_dir() / f"{self.config.language}.json"

    def load_language(self) -> Dict[str, str]:
        """
        Load translations for current language.

        Returns:
            Dictionary of translations
        """
        lang_file = self.get_language_file()

        if lang_file.exists():
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                logger.exception(
                    "Language loading failed for %s", lang_file, exc_info=exc
                )

        return {}

    def get_available_languages(self) -> list[str]:
        """
        Get list of available languages.

        Returns:
            List of language codes
        """
        lang_dir = self._get_i18n_dir()

        if not lang_dir.exists():
            return ["fr", "en"]

        languages = []
        for file in lang_dir.glob("*.json"):
            languages.append(file.stem)

        return sorted(languages)

    def migrate_from_old_config(self, old_config_path: Path) -> None:
        """
        Migrate old configuration (meta.json) to new format.

        Args:
            old_config_path: Path to old meta.json file
        """
        if not old_config_path.exists():
            return

        try:
            with open(old_config_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)

            if "language" in old_data:
                self.config.language = old_data["language"]

            if "affichage" in old_data:
                self.config.theme = old_data["affichage"]

            self.save()

        except (OSError, json.JSONDecodeError) as exc:
            logger.exception("Failed to migrate old configuration", exc_info=exc)


_config_manager: Optional[ConfigManager] = None
_config_lock = threading.Lock()


def get_config_manager() -> ConfigManager:
    """
    Get global configuration manager instance.

    Returns:
        ConfigManager instance
    """
    global _config_manager
    with _config_lock:
        if _config_manager is None:
            _config_manager = ConfigManager()
    return _config_manager


def reset_config_manager() -> None:
    """Reset global configuration manager instance."""
    global _config_manager
    _config_manager = None
