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
Internationalization (i18n) helper for S.O.K.
Provides a simple mechanism to load and retrieve translations.
"""

import logging
import threading
from typing import Dict, Optional
from sok.config import get_config_manager

# Configure logging
logger = logging.getLogger(__name__)


class Translator:
    """
    Handles loading and retrieving translations from the configuration.
    """

    def __init__(self) -> None:
        """Initialize the translator.

        Sets up the translation dictionary and loads initial translations.
        """
        self._translations: Dict[str, str] = {}
        self._loaded: bool = False
        self._lock = threading.Lock()
        self.reload()

    def reload(self) -> None:
        """
        Loads or reloads the language configuration and translation file.
        """
        with self._lock:
            try:
                config = get_config_manager()
                self._translations = config.load_language()
                self._loaded = True
                logger.debug(f"Translations loaded: {len(self._translations)} keys.")
            except (OSError, ValueError, KeyError) as e:
                logger.exception("Error loading translations", exc_info=e)
                if self._translations is None:
                    self._translations = {}

    def translate(self, key: str, default: Optional[str] = None) -> str:
        """
        Retrieves the translation for the given key.

        Args:
            key (str): The translation key (e.g., "app_title").
            default (str, optional): Text to return if key is missing.
                                     If None, returns the key itself.

        Returns:
            str: The translated text or the default/key.
        """
        if not self._loaded:
            self.reload()

        with self._lock:
            val = self._translations.get(key)
            if val is not None:
                return val

        return default if default is not None else key


_translator_instance = Translator()


def tr(key: str, default: Optional[str] = None) -> str:
    """
    Global helper function to translate a string.

    Args:
        key (str): The translation key.
        default (str, optional): Fallback text if the key is not found.

    Returns:
        str: Translated text.
    """
    return _translator_instance.translate(key, default)


def reload_language() -> None:
    """
    Forces a reload of the translation files (e.g. after language setting change).
    """
    _translator_instance.reload()
