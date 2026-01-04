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
Integrations components package.

This package contains UI components for integrating external services such as OAuth authentication, Discord presence, and update notifications.
"""

from sok.ui.components.integrations.discord import DiscordRPC
from sok.ui.components.integrations.oauth import OAuthManager
from sok.ui.components.integrations.updates import UpdateManager

__all__ = [
    "DiscordRPC",
    "OAuthManager",
    "UpdateManager",
]
