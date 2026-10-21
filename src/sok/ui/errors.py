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
Messages shown to the user when an online service fails.

The API errors (sok.core.exceptions) carry the technical message of the
service, in English, which goes to the log. The user gets a sentence in the
language of the app that says what to do.
"""

import re

from sok.config.api_registry import API_SERVICES
from sok.core.exceptions import (
    APIAuthenticationError,
    APIConnectionError,
    APIError,
    APINotFoundError,
    APIRateLimitError,
    APITimeoutError,
)
from sok.ui.i18n import tr

# Names of the API classes that differ from their service in the registry.
_ALIASES = {"imdb": "omdb"}


def _key(name: str) -> str:
    return re.sub(r"[^0-9a-z]", "", name.casefold())


def service_name(api_name: str) -> str:
    """Display name of a service, from a service id or an API class name.

    "google_books", "GoogleBooks" and "Google Books" all give "Google Books".
    """
    key = _key(api_name or "")
    key = _key(_ALIASES.get(key, key))
    for service_id, config in API_SERVICES.items():
        if key in (_key(service_id), _key(config.name)):
            return config.name
    if not key or key == "unknown":
        return tr("error_online_service", "The online service")
    return api_name


def error_message(exc: Exception) -> str:
    """Sentence for the user about an error, translated.

    Args:
        exc: The error raised by a worker.

    Returns:
        A message saying what failed and what to do for an API error, the
        text of the error otherwise.
    """
    if not isinstance(exc, APIError):
        return str(exc) or type(exc).__name__
    service = service_name(exc.api_name)
    if isinstance(exc, APIAuthenticationError):
        where = f"{tr('settings', 'Settings')} → {tr('api_keys', 'API Keys')}"
        return tr(
            "error_api_key",
            "{service}: the API key is missing or wrong. Check it in {where}.",
        ).format(service=service, where=where)
    if isinstance(exc, APIRateLimitError):
        if exc.retry_after:
            return tr(
                "error_api_quota_wait",
                "{service}: too many requests. Try again in {seconds} s.",
            ).format(service=service, seconds=exc.retry_after)
        return tr(
            "error_api_quota",
            "{service}: too many requests, or the quota of the day is used. "
            "Try again later.",
        ).format(service=service)
    if isinstance(exc, APITimeoutError):
        return tr(
            "error_api_timeout", "{service} did not answer in time. Try again."
        ).format(service=service)
    if isinstance(exc, APIConnectionError):
        return tr(
            "error_api_connection",
            "Cannot reach {service}. Check your internet connection.",
        ).format(service=service)
    if isinstance(exc, APINotFoundError):
        return tr("error_api_not_found", "{service} does not know this item.").format(
            service=service
        )
    return tr(
        "error_api_response", "{service} returned an error. Try again later."
    ).format(service=service)
