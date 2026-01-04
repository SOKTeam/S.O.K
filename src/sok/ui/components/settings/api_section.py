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
"""API connection section for settings page.

Manages API key input, OAuth authentication flows, and connection
status for all supported media services.
"""

import webbrowser
from typing import Dict
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
)
from sok.ui.components.base import Card, ActionButton
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.i18n import tr
from sok.ui.theme import card_shadow
from sok.core.constants import (
    SERVICE_TMDB,
    SERVICE_TVDB,
    SERVICE_LASTFM,
    API_KEY_CONFIG,
    SERVICES_WITH_DEFAULT_KEYS,
)
from sok.config.api_registry import (
    get_services_by_category,
    CATEGORY_LABELS,
    AuthType,
)
from sok.config.api_registry import get_service
from PySide6.QtWidgets import QInputDialog
from sok.config.api_registry import get_all_services


class ApiSection(QWidget):
    """API connection section for settings page.

    Manages API key input, OAuth authentication flows, and connection
    status for all supported media services.
    """

    def __init__(self, config, oauth_manager, parent=None):
        """Initialize the API section.

        Args:
            config: Configuration manager instance.
            oauth_manager: OAuth manager for authentication.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._config = config
        self._oauth = oauth_manager
        self._api_cat_labels: Dict[str, QLabel] = {}
        self._build()
        self._wire_oauth()

    def _wire_oauth(self):
        """Connect OAuth manager signals."""
        self._oauth.auth_success.connect(self._on_auth_success)
        self._oauth.auth_error.connect(self._on_auth_error)
        self._oauth.auth_started.connect(self._on_auth_started)

    def _build(self):
        """Build the section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = make_section_label("api_keys", "API KEYS")
        layout.addWidget(self.label)

        try:
            services_by_cat = get_services_by_category()
            for category, services in services_by_cat.items():
                cat_data = CATEGORY_LABELS.get(category, (category, category))
                cat_label = QLabel()
                cat_label.setProperty("tr_key", cat_data[0])
                cat_label.setProperty("tr_default", cat_data[1])
                cat_label.setObjectName("CategoryLabel")
                layout.addWidget(cat_label)
                self._api_cat_labels[category] = cat_label

                cat_card = Card()
                for service in services:
                    desc_key = f"api_desc_{service.id}"
                    translated_desc = tr(desc_key, service.description)

                    if service.auth_type in (
                        AuthType.OAUTH,
                        AuthType.BEARER,
                        AuthType.SESSION,
                    ):
                        row = self._create_oauth_row(
                            service.name, translated_desc, service.id
                        )
                    else:
                        row = self._create_api_key_row(
                            service.name,
                            translated_desc,
                            service.id,
                            service.config_key,
                            service.api_key_url,
                        )
                    cat_card.add(row)
                cat_card.setGraphicsEffect(card_shadow())
                cat_card.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                )
                layout.addWidget(cat_card)
        except ImportError:
            api_card = Card()
            api_card.add(self._create_oauth_row("TMDB", "Video metadata", SERVICE_TMDB))
            api_card.add(
                self._create_oauth_row("Last.fm", "Music metadata", SERVICE_LASTFM)
            )
            api_card.add(
                self._create_oauth_row("TVDB", "TV series metadata", SERVICE_TVDB)
            )
            api_card.setGraphicsEffect(card_shadow())
            api_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            layout.addWidget(api_card)

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

    def _create_oauth_row(self, title: str, subtitle: str, service: str) -> QWidget:
        """Create a row for OAuth service.

        Args:
            title: Service name.
            subtitle: Service description.
            service: Service identifier.

        Returns:
            Widget containing the row.
        """
        row = QWidget()
        row.setFixedHeight(56)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        lbl_container = QWidget()
        lbl_container.setMinimumWidth(180)
        lbl_layout = QVBoxLayout(lbl_container)
        lbl_layout.setContentsMargins(0, 0, 0, 0)
        lbl_layout.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("RowTitle")

        status_lbl = QLabel()
        status_lbl.setObjectName("RowSubtitle")
        setattr(self, f"_{service}_status", status_lbl)

        lbl_layout.addWidget(title_lbl)
        lbl_layout.addWidget(status_lbl)
        layout.addWidget(lbl_container)
        layout.addStretch()

        connect_btn = ActionButton("")
        connect_btn.setProperty("tr_key", "connect")
        connect_btn.setProperty("tr_default", "Connect")
        connect_btn.setText(tr("connect", "Connect"))
        connect_btn.clicked.connect(lambda: self._connect_service(service))
        setattr(self, f"_{service}_connect_btn", connect_btn)
        layout.addWidget(connect_btn)

        disconnect_btn = ActionButton("")
        disconnect_btn.setProperty("tr_key", "disconnect")
        disconnect_btn.setProperty("tr_default", "Disconnect")
        disconnect_btn.setObjectName("DestructiveBtn")
        disconnect_btn.setText(tr("disconnect", "Disconnect"))
        disconnect_btn.clicked.connect(lambda: self._disconnect_service(service))
        disconnect_btn.setVisible(False)
        setattr(self, f"_{service}_disconnect_btn", disconnect_btn)
        layout.addWidget(disconnect_btn)

        return row

    def _create_api_key_row(
        self,
        title: str,
        subtitle: str,
        service: str,
        config_key: str,
        api_key_url: str = "",
    ) -> QWidget:
        """Create a row for API key input.

        Args:
            title: Service name.
            subtitle: Service description.
            service: Service identifier.
            config_key: Configuration key for API key.
            api_key_url: URL to obtain API key.

        Returns:
            Widget containing the row.
        """
        row = QWidget()
        has_default_key = service in SERVICES_WITH_DEFAULT_KEYS
        row.setFixedHeight(68 if has_default_key else 56)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        lbl_container = QWidget()
        lbl_container.setMinimumWidth(200)
        lbl_layout = QVBoxLayout(lbl_container)
        lbl_layout.setContentsMargins(0, 0, 0, 0)
        lbl_layout.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("RowTitle")

        status_lbl = QLabel()
        status_lbl.setObjectName("RowSubtitle")
        setattr(self, f"_{service}_status", status_lbl)

        lbl_layout.addWidget(title_lbl)
        lbl_layout.addWidget(status_lbl)

        if has_default_key:
            default_lbl = QLabel(tr("built_in_key", "Built-in key by default"))
            default_lbl.setProperty("tr_key", "built_in_key")
            default_lbl.setProperty("tr_default", "Built-in key by default")
            default_lbl.setStyleSheet(
                "color: #6272a4; font-size: 10px; font-style: italic;"
            )
            setattr(self, f"_{service}_default_lbl", default_lbl)
            lbl_layout.addWidget(default_lbl)

        layout.addWidget(lbl_container)
        layout.addStretch()

        if config_key:
            input_field = QLineEdit()
            input_field.setMinimumWidth(220)
            input_field.setObjectName("SettingsInput")
            input_field.setEchoMode(QLineEdit.EchoMode.Password)
            setattr(self, f"_{service}_input", input_field)
            layout.addWidget(input_field)

            if api_key_url:
                get_key_btn = ActionButton("")
                get_key_btn.setProperty("tr_key", "get")
                get_key_btn.setProperty("tr_default", "Get")
                get_key_btn.setText(tr("get", "Get"))
                get_key_btn.clicked.connect(
                    lambda checked, url=api_key_url: webbrowser.open(url)
                )
                setattr(self, f"_{service}_get_btn", get_key_btn)
                layout.addWidget(get_key_btn)
        else:
            info_lbl = QLabel(subtitle)
            info_lbl.setObjectName("RowSubtitle")
            info_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
            layout.addWidget(info_lbl)
        return row

    def _connect_service(self, service: str):
        """Initiate connection to a service.

        Args:
            service: Service identifier.
        """
        service_config = self._get_service_config(service)
        if service_config:
            config_key = service_config.config_key
        else:
            config_key = API_KEY_CONFIG.get(service, "")

        api_key = self._config.get(config_key, "") if config_key else ""
        if not api_key:
            self._show_api_key_dialog(service)
        else:
            api_secret = ""
            if service_config and service_config.requires_secret:
                api_secret = self._config.get(service_config.secret_config_key, "")
            self._oauth.authenticate(service, api_key, api_secret)

    def _show_api_key_dialog(self, service: str):
        """Show dialog to input API key.

        Args:
            service: Service identifier.
        """

        service_config = self._get_service_config(service)
        if service_config:
            name = service_config.name
            url = service_config.api_key_url
            config_key = service_config.config_key
        else:
            fallback_info = {
                SERVICE_TMDB: (
                    "TMDB",
                    "https://www.themoviedb.org/settings/api",
                    API_KEY_CONFIG.get(SERVICE_TMDB, ""),
                ),
                SERVICE_LASTFM: (
                    "Last.fm",
                    "https://www.last.fm/api/account/create",
                    API_KEY_CONFIG.get(SERVICE_LASTFM, ""),
                ),
                SERVICE_TVDB: (
                    "TVDB",
                    "https://thetvdb.com/api-information",
                    API_KEY_CONFIG.get(SERVICE_TVDB, ""),
                ),
            }
            name, url, config_key = fallback_info.get(service, (service, "", ""))

        if url:
            reply = QMessageBox.question(
                self,
                tr("api_key_required", "{name} API key required").format(name=name),
                tr(
                    "api_key_needed_msg",
                    "To connect to {name}, you need an API key.\n\n",
                ).format(name=name)
                + tr(
                    "open_url_confirm",
                    "Would you like to open {name} to create an API key?",
                ).format(name=name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                webbrowser.open(url)

        api_key, ok = QInputDialog.getText(
            self,
            f"{name} API Key",
            tr("enter_api_key", "Enter your {name} API key:").format(name=name),
            QLineEdit.EchoMode.Normal,
        )
        if ok and api_key:
            self._config.set(config_key, api_key.strip())
            api_secret = ""
            if service_config and service_config.requires_secret:
                api_secret, ok_secret = QInputDialog.getText(
                    self,
                    tr("api_secret_title", "{name} API Secret").format(name=name),
                    tr("enter_api_secret", "Enter your {name} API secret:").format(
                        name=name
                    ),
                    QLineEdit.EchoMode.Normal,
                )
                if ok_secret and api_secret:
                    self._config.set(
                        service_config.secret_config_key, api_secret.strip()
                    )
            self._oauth.authenticate(
                service, api_key.strip(), api_secret.strip() if api_secret else ""
            )

    def _disconnect_service(self, service: str):
        """Disconnect from a service.

        Args:
            service: Service identifier.
        """
        reply = QMessageBox.question(
            self,
            tr("disconnect_title", "Disconnect"),
            tr(
                "disconnect_confirm",
                "Are you sure you want to disconnect from this service?",
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            service_config = self._get_service_config(service)
            if service_config:
                config_key = service_config.config_key
                session_key = service_config.session_key or f"{service}_session"
            else:
                config_key = API_KEY_CONFIG.get(service, "")
                session_key = f"{service}_session"
            if config_key:
                self._config.set(config_key, "")
            self._config.set(session_key, "")
            if service_config and service_config.requires_secret:
                self._config.set(service_config.secret_config_key, "")

            status_lbl = getattr(self, f"_{service}_status", None)
            connect_btn = getattr(self, f"_{service}_connect_btn", None)
            disconnect_btn = getattr(self, f"_{service}_disconnect_btn", None)
            if status_lbl:
                status_lbl.setText(tr("not_connected", "Not connected"))
                status_lbl.setStyleSheet("")
            if connect_btn:
                connect_btn.setVisible(True)
            if disconnect_btn:
                disconnect_btn.setVisible(False)

    def _on_auth_started(self, service: str):
        """Handle authentication started.

        Args:
            service: Service identifier.
        """
        status_lbl = getattr(self, f"_{service}_status", None)
        if status_lbl:
            status_lbl.setText(tr("connection_in_progress", "Connecting..."))
            status_lbl.setStyleSheet("color: #FFB86C;")

    def _on_auth_success(self, service: str, data: dict):
        """Handle authentication success.

        Args:
            service: Service identifier.
            data: Authentication result data.
        """
        status_lbl = getattr(self, f"_{service}_status", None)
        connect_btn = getattr(self, f"_{service}_connect_btn", None)
        disconnect_btn = getattr(self, f"_{service}_disconnect_btn", None)

        session_key = f"{service}_session"
        self._config.set(session_key, str(data))
        username = data.get("username", "")
        if status_lbl:
            if username:
                status_lbl.setText(f"{tr('connected', 'Connected')} ({username})")
            else:
                status_lbl.setText(tr("connected", "Connected"))
            status_lbl.setStyleSheet("color: #50FA7B;")
        if connect_btn:
            connect_btn.setVisible(False)
        if disconnect_btn:
            disconnect_btn.setVisible(True)
        QMessageBox.information(
            self,
            tr("connection_success", "Connection successful"),
            tr("connected_to", "You are now connected to {service}!").format(
                service=service.upper()
            ),
        )

    def _on_auth_error(self, service: str, error: str):
        """Handle authentication error.

        Args:
            service: Service identifier.
            error: Error message.
        """
        status_lbl = getattr(self, f"_{service}_status", None)
        if status_lbl:
            status_lbl.setText(tr("error", "Error"))
            status_lbl.setStyleSheet("color: #FF6B6B;")
        QMessageBox.warning(
            self,
            tr("connection_error", "Connection error"),
            f"{tr('connection_failed', 'Failed to connect:')}\n{error}",
        )

    def load(self):
        """Load settings values into UI."""
        try:
            all_services = get_all_services()
        except ImportError:
            all_services = None
        if not all_services:
            return
        for service_config in all_services:
            service = service_config.id
            status_lbl = getattr(self, f"_{service}_status", None)
            connect_btn = getattr(self, f"_{service}_connect_btn", None)
            disconnect_btn = getattr(self, f"_{service}_disconnect_btn", None)
            input_field = getattr(self, f"_{service}_input", None)

            if input_field:
                if service in SERVICES_WITH_DEFAULT_KEYS:
                    input_field.setPlaceholderText(
                        tr("custom_key_optional", "Custom key (Optional)...")
                    )
                    input_field.setToolTip(
                        tr(
                            "custom_key_tooltip",
                            "A key is already included. Enter a value only to use your own key.",
                        )
                    )
                else:
                    input_field.setPlaceholderText(
                        tr("your_api_key", "Your API key...")
                    )
                current_key = (
                    self._config.get_user_value(service_config.config_key, "")
                    if service_config.config_key
                    else ""
                )
                input_field.setText(current_key)

            if service_config.auth_type in (
                AuthType.OAUTH,
                AuthType.BEARER,
                AuthType.SESSION,
            ):
                session_key = service_config.session_key or f"{service}_session"
                session = self._config.get(session_key, "")
                api_key = (
                    self._config.get(service_config.config_key, "")
                    if service_config.config_key
                    else ""
                )
                if session and api_key:
                    if status_lbl:
                        status_lbl.setText(tr("connected", "Connected"))
                        status_lbl.setStyleSheet("color: #50FA7B;")
                    if connect_btn:
                        connect_btn.setVisible(False)
                    if disconnect_btn:
                        disconnect_btn.setVisible(True)
                elif api_key:
                    if status_lbl:
                        status_lbl.setText(tr("key_configured", "Key configured"))
                        status_lbl.setStyleSheet("")
                    if connect_btn:
                        connect_btn.setVisible(True)
                    if disconnect_btn:
                        disconnect_btn.setVisible(False)
                else:
                    if status_lbl:
                        status_lbl.setText(tr("not_connected", "Not connected"))
                        status_lbl.setStyleSheet("")
                    if connect_btn:
                        connect_btn.setVisible(True)
                    if disconnect_btn:
                        disconnect_btn.setVisible(False)
            elif service_config.auth_type == AuthType.API_KEY:
                if not service_config.config_key:
                    if status_lbl:
                        status_lbl.setText(tr("available_free", "Available (free)"))
                        status_lbl.setStyleSheet("color: #50FA7B;")
                else:
                    api_key = self._config.get(service_config.config_key, "")
                    if api_key:
                        if status_lbl:
                            status_lbl.setText(tr("operational", "Operational"))
                            status_lbl.setStyleSheet("color: #50FA7B;")
                    else:
                        if status_lbl:
                            status_lbl.setText(tr("not_configured", "Not configured"))
                            status_lbl.setStyleSheet("")

    def retranslate(self):
        """Update translatable UI text."""
        self.label.setText(tr("api_keys", "API KEYS"))
        for label in self._api_cat_labels.values():
            tr_key = label.property("tr_key")
            default = label.property("tr_default")
            if tr_key:
                label.setText(tr(tr_key, default or "").upper())
        for attr in dir(self):
            if (
                attr.endswith("_connect_btn")
                or attr.endswith("_disconnect_btn")
                or attr.endswith("_get_btn")
            ):
                btn = getattr(self, attr)
                if isinstance(btn, ActionButton):
                    tr_key = btn.property("tr_key")
                    tr_default = btn.property("tr_default")
                    if tr_key:
                        btn.setText(tr(tr_key, tr_default or ""))
        self.load()
