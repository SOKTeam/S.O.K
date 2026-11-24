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
"""Application pages for the main content area.

Contains the main page widgets: HomePage and SettingsPage; the media pages
are the subclasses of BatchPage.
"""

from sok.ui.pages.home_page import HomePage
from sok.ui.pages.settings_page import SettingsPage

__all__ = ["HomePage", "SettingsPage"]
