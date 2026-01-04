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
"""API preferences section for settings page.

Allows users to select their preferred API provider for each media type
(video, music, books, games).
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from sok.ui.components.base import Card
from sok.ui.components.inputs import ModernComboBox
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.i18n import tr
from sok.ui.theme import card_shadow
from sok.core.constants import SERVICE_LASTFM
from sok.config.api_registry import get_services_by_media_type
from sok.config.api_registry import get_service


class ApiPreferencesSection(QWidget):
    """Preferred API selection by media type.

    Allows users to select their preferred API provider for each
    media type (video, music, books, games).
    """

    def __init__(self, config, parent=None):
        """Initialize the API preferences section.

        Args:
            config: Configuration manager instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._config = config
        self._build()

    def _build(self):
        """Build the section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = make_section_label("preferred_api", "PREFERRED API")
        layout.addWidget(self.label)

        self.card = Card()
        try:
            categories = [
                ("video", "videos", "Video", "preferred_api_video"),
                ("music", "music", "Music", "preferred_api_music"),
                ("books", "books", "Books", "preferred_api_books"),
                ("games", "games", "Games", "preferred_api_games"),
            ]
            for media_type, tr_key, default, config_key in categories:
                services = get_services_by_media_type(media_type)
                if services:
                    self.card.add(
                        self._create_api_selector_row(
                            tr_key, default, config_key, services
                        )
                    )
        except ImportError:
            pass

        self.card.setGraphicsEffect(card_shadow())
        self.card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.card)

    def _create_api_selector_row(
        self, tr_key: str, default: str, config_key: str, services: list
    ) -> QWidget:
        """Create a row with API selector combo box.

        Args:
            tr_key: Translation key for the label.
            default: Default label text.
            config_key: Configuration key for the preference.
            services: List of available services.

        Returns:
            Widget containing the row.
        """
        row = QWidget()
        row.setFixedHeight(44)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        lbl = QLabel()
        lbl.setProperty("tr_key", tr_key)
        lbl.setProperty("tr_default", default)
        lbl.setObjectName("RowTitle")
        lbl.setMinimumWidth(120)
        layout.addWidget(lbl)

        layout.addStretch()

        warning_lbl = QLabel()
        warning_lbl.setStyleSheet("color: #FFB86C; font-size: 11px; font-weight: bold;")
        warning_lbl.setVisible(False)
        layout.addWidget(warning_lbl)

        combo = ModernComboBox()
        combo.setMinimumWidth(180)
        combo.setObjectName("SettingsCombo")

        current_value = self._config.get(config_key, "")
        current_index = 0
        for i, service in enumerate(services):
            combo.addItem(service.name, service.id)
            if service.id == current_value:
                current_index = i
        combo.setCurrentIndex(current_index)

        def validate_selection(index: int):
            """Validate that selected API has required configuration.

            Args:
                index: Selected combo box index.
            """
            service_id = combo.itemData(index)
            service_config = self._get_service_config(service_id)
            is_valid = True
            missing_reason = ""
            if service_config:
                if service_config.config_key and not self._config.get(
                    service_config.config_key, ""
                ):
                    is_valid = False
                    missing_reason = tr("api_key_needed", "API key required")
                if service_config.requires_secret and service_id != SERVICE_LASTFM:
                    secret = self._config.get(service_config.secret_config_key, "")
                    if not secret:
                        is_valid = False
                        missing_reason = (
                            tr("secret_key_needed", "Secret key required")
                            if not missing_reason
                            else tr("keys_missing", "Keys missing")
                        )
            if not is_valid:
                warning_lbl.setText(f"⚠️ {missing_reason}")
                warning_lbl.setToolTip(
                    tr(
                        "api_needs_config",
                        "The {service_id} API requires configuration.",
                    ).format(service_id=service_id)
                )
                warning_lbl.setVisible(True)
            else:
                warning_lbl.setVisible(False)

        validate_selection(current_index)

        def on_change(index: int):
            """Handle API selection change.

            Args:
                index: New selected combo box index.
            """
            service_id = combo.itemData(index)
            self._config.set(config_key, service_id)
            validate_selection(index)

        combo.currentIndexChanged.connect(on_change)
        layout.addWidget(combo)
        return row

    def _get_service_config(self, service_id: str):
        """Get service configuration from registry.

        Args:
            service_id: Service identifier.

        Returns:
            Service configuration or None.
        """
        try:
            return get_service(service_id)
        except ImportError:
            return None

    def load(self):
        """Load settings values into UI."""
        pass

    def retranslate(self):
        """Update translatable UI text."""
        self.label.setText(tr("preferred_api", "PREFERRED API"))
        layout = self.card.layout()
        if not layout:
            return
        for i in range(layout.count()):
            item = layout.itemAt(i)
            row = item.widget() if item else None
            if not row:
                continue
            lbl = row.findChild(QLabel)
            if lbl:
                tr_key = lbl.property("tr_key")
                default = lbl.property("tr_default")
                lbl.setText(tr(tr_key, default or ""))
