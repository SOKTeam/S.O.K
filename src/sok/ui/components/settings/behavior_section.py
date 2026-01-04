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
"""Behavior section for settings page.

Provides toggle controls for various application behaviors like
auto-organize, folder creation, poster downloads, and operation logging.
"""

from __future__ import annotations

from typing import Dict
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from sok.ui.components.base import Card, Toggle
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.i18n import tr
from sok.ui.theme import card_shadow


class BehaviorSection(QWidget):
    """Behavior section with toggle controls.

    Provides toggles for various application behaviors like
    auto-organize, folder creation, poster downloads, and logging.
    """

    def __init__(self, config, parent=None):
        """Initialize the behavior section.

        Args:
            config: Configuration manager instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._config = config
        self._toggles: Dict[str, Toggle] = {}
        self._build()

    def _build(self):
        """Build the section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = make_section_label("behavior", "BEHAVIOR")
        layout.addWidget(self.label)

        card = Card()
        for tr_key, default, config_key, enabled in [
            ("auto_organize", "Automatic organization", "auto_organize", False),
            (
                "create_missing_folders",
                "Create missing folders",
                "create_folders",
                True,
            ),
            ("download_posters", "Download posters", "download_posters", False),
            (
                "backup_before_rename",
                "Backup before renaming",
                "backup_before_rename",
                True,
            ),
            ("skip_duplicates", "Skip duplicates", "skip_duplicates", True),
            ("log_operations", "Log operations", "log_operations", True),
        ]:
            card.add(self._create_toggle_row(tr_key, default, config_key, enabled))

        card.setGraphicsEffect(card_shadow())
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(card)

    def _create_toggle_row(
        self, tr_key: str, default: str, config_key: str, enabled: bool = True
    ) -> QWidget:
        """Create a row with label and toggle.

        Args:
            tr_key: Translation key for the label.
            default: Default label text.
            config_key: Configuration key for the toggle.
            enabled: Whether the toggle is enabled.

        Returns:
            Widget containing the row.
        """
        row = QWidget()
        row.setFixedHeight(32)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 0, 12, 0)

        title_lbl = QLabel(tr(tr_key, default))
        title_lbl.setProperty("tr_key", tr_key)
        title_lbl.setProperty("tr_default", default)
        title_lbl.setObjectName("RowTitle")

        # Gray out text if disabled
        if not enabled:
            title_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.4);")
            title_lbl.setToolTip(tr("coming_soon", "Coming soon"))

        toggle = Toggle()
        toggle.setProperty("config_key", config_key)
        toggle.setEnabled(enabled)
        if enabled:
            toggle.toggled.connect(
                lambda checked, k=config_key: self._config.set(k, checked)
            )
        self._toggles[config_key] = toggle

        layout.addWidget(title_lbl)
        layout.addStretch()
        layout.addWidget(toggle)
        return row

    def load(self):
        """Load settings values into UI."""
        for key, toggle in self._toggles.items():
            toggle.blockSignals(True)
            toggle.setChecked(self._config.get(key, False))
            toggle.blockSignals(False)

    def retranslate(self):
        """Update translatable UI text."""
        self.label.setText(tr("behavior", "BEHAVIOR"))
        for toggle in self._toggles.values():
            parent = toggle.parentWidget()
            if not parent:
                continue
            lbl = parent.findChild(QLabel)
            if lbl:
                tr_key = lbl.property("tr_key")
                default = lbl.property("tr_default")
                lbl.setText(tr(tr_key, default or ""))
        self.load()
