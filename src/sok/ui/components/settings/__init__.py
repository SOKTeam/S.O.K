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
"""Settings page section components.

Contains modular sections for the settings page: API, paths,
formats, appearance, behavior, and about sections.
"""

from sok.ui.components.settings.api_section import ApiSection
from sok.ui.components.settings.api_preferences_section import ApiPreferencesSection
from sok.ui.components.settings.paths_section import PathsSection
from sok.ui.components.settings.formats_section import FormatsSection
from sok.ui.components.settings.appearance_section import AppearanceSection
from sok.ui.components.settings.behavior_section import BehaviorSection
from sok.ui.components.settings.about_section import AboutSection

__all__ = [
    "ApiSection",
    "ApiPreferencesSection",
    "PathsSection",
    "FormatsSection",
    "AppearanceSection",
    "BehaviorSection",
    "AboutSection",
]
