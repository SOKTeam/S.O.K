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
Custom exceptions for the S.O.K. project.

This module defines an exception hierarchy to improve
error handling and facilitate debugging.
"""


class SOKBaseError(Exception):
    """Base class for all S.O.K. exceptions."""

    pass


class APIError(SOKBaseError):
    """Base exception for API errors."""

    def __init__(self, message: str, api_name: str = "unknown"):
        """Initialize an API error.

        Args:
            message: Error description.
            api_name: Name of the API that raised the error.
        """
        self.api_name = api_name
        super().__init__(message)


class APINotFoundError(APIError):
    """Exception raised when the requested API is not found."""

    def __init__(self, message: str, api_name: str = "unknown"):
        """Initialize an API not found error.

        Args:
            message: Error description.
            api_name: Name of the missing API.
        """
        super().__init__(message, api_name)


class APIConnectionError(APIError):
    """Exception raised on API connection errors."""

    def __init__(self, message: str, api_name: str = "unknown"):
        """Initialize an API connection error.

        Args:
            message: Error description.
            api_name: Name of the API with connection issues.
        """
        super().__init__(message, api_name)


class APITimeoutError(APIError):
    """Exception raised on API timeout."""

    def __init__(self, message: str, api_name: str = "unknown"):
        """Initialize an API timeout error.

        Args:
            message: Error description.
            api_name: Name of the API that timed out.
        """
        super().__init__(message, api_name)


class APIRateLimitError(APIError):
    """Exception raised when API rate limit is exceeded."""

    def __init__(self, message: str, api_name: str = "unknown", retry_after: int = 0):
        """Initialize an API rate limit error.

        Args:
            message: Error description.
            api_name: Name of the rate-limited API.
            retry_after: Seconds to wait before retrying.
        """
        self.retry_after = retry_after
        super().__init__(message, api_name)


class APIAuthenticationError(APIError):
    """Exception raised on authentication errors."""

    def __init__(self, message: str, api_name: str = "unknown"):
        """Initialize an API authentication error.

        Args:
            message: Error description.
            api_name: Name of the API with auth issues.
        """
        super().__init__(message, api_name)


class APIResponseError(APIError):
    """Exception raised on response parsing errors."""

    def __init__(self, message: str, api_name: str = "unknown"):
        """Initialize an API response error.

        Args:
            message: Error description.
            api_name: Name of the API with response issues.
        """
        super().__init__(message, api_name)


class MediaError(SOKBaseError):
    """Base exception for media-related errors."""

    pass


class UnsupportedMediaTypeError(MediaError):
    """Exception raised when the media type is not supported."""

    def __init__(self, message: str):
        """Initialize an unsupported media type error.

        Args:
            message: Error description.
        """
        super().__init__(message)


class MediaNotFoundError(MediaError):
    """Exception raised when a media item is not found."""

    def __init__(self, message: str):
        """Initialize a media not found error.

        Args:
            message: Error description.
        """
        super().__init__(message)


class FileOperationError(SOKBaseError):
    """Base exception for file operation errors."""

    pass


class FileNotFoundError(FileOperationError):
    """Exception raised when a file is not found."""

    def __init__(self, message: str, file_path: str = ""):
        """Initialize a file not found error.

        Args:
            message: Error description.
            file_path: Path to the missing file.
        """
        self.file_path = file_path
        super().__init__(message)


class FilePermissionError(FileOperationError):
    """Exception raised on permission errors."""

    def __init__(self, message: str, file_path: str = ""):
        """Initialize a file permission error.

        Args:
            message: Error description.
            file_path: Path to the file with permission issues.
        """
        self.file_path = file_path
        super().__init__(message)


class ConfigurationError(SOKBaseError):
    """Exception raised on configuration errors."""

    pass


class MissingConfigurationError(ConfigurationError):
    """Exception raised when a required configuration is missing."""

    def __init__(self, message: str, config_key: str = ""):
        """Initialize a missing configuration error.

        Args:
            message: Error description.
            config_key: Name of the missing configuration key.
        """
        self.config_key = config_key
        super().__init__(message)
