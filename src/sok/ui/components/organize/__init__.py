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
Modular components for the organization page.

This module splits OrganizePage into reusable widgets to improve
maintainability and testability of the code.
"""

from sok.ui.components.organize.search_panel import SearchPanel
from sok.ui.components.organize.options_panel import OptionsPanel
from sok.ui.components.organize.log_widget import OrganizeLogWidget

__all__ = [
    "SearchPanel",
    "OptionsPanel",
    "OrganizeLogWidget",
]
