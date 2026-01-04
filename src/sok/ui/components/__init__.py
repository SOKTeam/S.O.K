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
UI Components package.

This package contains reusable UI components for the S.O.K application, such as base widgets, dialogs, input fields, layouts, preview panels, search bars, sidebars, and window elements.
"""

from sok.ui.components.base import Card, Row, Toggle, ActionButton
from sok.ui.components.dialogs import SearchResultCard, SearchResultsDialog
from sok.ui.components.inputs import ModernComboBox, SearchBar, FileItemRow, DropZone
from sok.ui.components.layouts import FlowLayout
from sok.ui.components.preview import FileRow
from sok.ui.components.search import (
    ImageLoaderWorker,
    SearchResultRow,
    SelectedMediaWidget,
)
from sok.ui.components.sidebar import SidebarButton, MenuButton
from sok.ui.components.window import WindowControlButton, StopPropagationScrollArea

__all__ = [
    "Card",
    "Row",
    "Toggle",
    "ActionButton",
    "SearchResultCard",
    "SearchResultsDialog",
    "ModernComboBox",
    "SearchBar",
    "FileItemRow",
    "DropZone",
    "FlowLayout",
    "FileRow",
    "ImageLoaderWorker",
    "SearchResultRow",
    "SelectedMediaWidget",
    "SidebarButton",
    "MenuButton",
    "WindowControlButton",
    "StopPropagationScrollArea",
]
