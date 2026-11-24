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


def plural_form(language: str, n: int) -> str:
    """Return the plural form of a number in a language.

    "one", "few", "many" or "other", after the CLDR rules of the eight
    languages of the app: French puts 0 with 1; Polish and Russian have a
    form for 2 to 4.

    Args:
        language: Language code ("fr", "pl"…).
        n: The number.
    """
    n = abs(n)
    if language == "fr":
        return "one" if n in (0, 1) else "other"
    if language in ("pl", "ru"):
        if language == "ru" and n % 10 == 1 and n % 100 != 11:
            return "one"
        if language == "pl" and n == 1:
            return "one"
        if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            return "few"
        return "many"
    return "one" if n == 1 else "other"


def trn(key: str, n: int, one: str, other: str) -> str:
    """Translate a text that depends on a number, and put the number in it.

    The translations are "<key>_one", "<key>_few", "<key>_many" and
    "<key>_other"; a language without a form uses "_other", then "_many".
    "{n}" in the text is replaced by the number.

    Args:
        key: Base key, such as "batch_title_movies".
        n: The number.
        one: English text for 1.
        other: English text for any other number.
    """
    language = get_config_manager().get("language", "en")
    form = plural_form(language, n)
    default = one if form == "one" else other
    for suffix in (form, "other", "many"):
        text = _translator_instance.translate(f"{key}_{suffix}", None)
        if text != f"{key}_{suffix}":
            return text.replace("{n}", str(n))
    return default.replace("{n}", str(n))


def reload_language() -> None:
    """
    Forces a reload of the translation files (e.g. after language setting change).
    """
    _translator_instance.reload()
