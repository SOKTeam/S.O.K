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
"""Sources section of the settings: the services S.O.K searches.

A dotted sheet per type of media. Its first line picks the service searched
first ("Searched first ..... TMDB  TVDB  OMDb", the chosen one in ink), then
a line per service with its state at the end ("Built-in key", "Your key",
"Connected", "To set up", "Free"), in the caution color when the service
searched first lacks its key. A click opens the line of a service: what it
gives, and its key field or its connect keys.
"""

import webbrowser
from typing import Dict, List
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
)
from sok.ui.components.base import KeyButton
from sok.ui.components.settings.layout import ChoiceLine, SheetRow
from sok.ui.i18n import tr
from sok.ui.theme import set_tone
from sok.ui import message_box
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
from sok.core.media_manager import reset_media_manager

OAUTH_TYPES = (AuthType.OAUTH, AuthType.BEARER, AuthType.SESSION)

# The setting of the service searched first, by type of media.
PREFERRED_KEYS = {
    "video": "preferred_api_video",
    "music": "preferred_api_music",
    "books": "preferred_api_books",
    "games": "preferred_api_games",
}


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
        self._rows: Dict[str, SheetRow] = {}
        self._abouts: List[QLabel] = []
        self._keys: List[KeyButton] = []
        self._first_lines: Dict[str, ChoiceLine] = {}
        self._build()
        self._wire_oauth()

    def _wire_oauth(self):
        """Connect OAuth manager signals."""
        self._oauth.auth_success.connect(self._on_auth_success)
        self._oauth.auth_error.connect(self._on_auth_error)
        self._oauth.auth_started.connect(self._on_auth_started)

    def _build(self):
        """A sheet per type of media: a line per service, opened on a click."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for category, services in get_services_by_category().items():
            cat_data = CATEGORY_LABELS.get(category, (category, category))
            cat_label = QLabel()
            cat_label.setProperty("tr_key", cat_data[0])
            cat_label.setProperty("tr_default", cat_data[1])
            cat_label.setObjectName("CategoryLabel")
            layout.addWidget(cat_label)
            self._api_cat_labels[category] = cat_label
            if category in PREFERRED_KEYS and len(services) > 1:
                first = ChoiceLine([service.id for service in services])
                first.choice.set_texts(service.name for service in services)
                first.choice.chosen.connect(
                    lambda service_id, c=category: self._prefer(c, service_id)
                )
                self._first_lines[category] = first
                layout.addWidget(first)
            for service in services:
                row = SheetRow()
                row.name.setText(service.name)
                row.clicked.connect(lambda s=service.id: self._toggle(s))
                setattr(self, f"_{service.id}_status", row.value)
                self._fill_details(row, service)
                self._rows[service.id] = row
                layout.addWidget(row)

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

    def _toggle(self, service: str) -> None:
        """Open the line of a service, or close it if it is open."""
        row = self._rows[service]
        opening = not row.is_open()
        for other in self._rows.values():
            other.set_open(False)
        row.set_open(opening)

    def _fill_details(self, row: SheetRow, service) -> None:
        """What a line shows once open: what the service gives, then its key
        field or its connect keys, and the key that makes it the default."""
        details = row.details_layout
        about = QLabel()
        about.setObjectName("SettingHint")
        about.setWordWrap(True)
        about.setProperty("tr_key", f"api_desc_{service.id}")
        about.setProperty("tr_default", service.description)
        details.addWidget(about)
        self._abouts.append(about)

        keys = QHBoxLayout()
        keys.setSpacing(8)
        if service.auth_type in OAUTH_TYPES:
            connect_btn = KeyButton("", small=True)
            connect_btn.setProperty("tr_key", "connect")
            connect_btn.setProperty("tr_default", "Connect")
            connect_btn.clicked.connect(lambda: self._connect_service(service.id))
            setattr(self, f"_{service.id}_connect_btn", connect_btn)
            disconnect_btn = KeyButton("", small=True)
            disconnect_btn.set_danger(True)
            disconnect_btn.setProperty("tr_key", "disconnect")
            disconnect_btn.setProperty("tr_default", "Disconnect")
            disconnect_btn.clicked.connect(lambda: self._disconnect_service(service.id))
            disconnect_btn.setVisible(False)
            setattr(self, f"_{service.id}_disconnect_btn", disconnect_btn)
            keys.addWidget(connect_btn)
            keys.addWidget(disconnect_btn)
            self._keys.extend([connect_btn, disconnect_btn])
        elif service.config_key:
            input_field = QLineEdit()
            input_field.setObjectName("SettingsInput")
            input_field.setEchoMode(QLineEdit.EchoMode.Password)
            # Saved on Enter or when the field loses the focus.
            input_field.editingFinished.connect(
                lambda key=service.config_key, field=input_field: self._save_key(
                    key, field
                )
            )
            setattr(self, f"_{service.id}_input", input_field)
            keys.addWidget(input_field, 1)
            if service.api_key_url:
                get_key_btn = KeyButton("", small=True)
                get_key_btn.setProperty("tr_key", "get")
                get_key_btn.setProperty("tr_default", "Get")
                get_key_btn.clicked.connect(
                    lambda _=False, url=service.api_key_url: webbrowser.open(url)
                )
                setattr(self, f"_{service.id}_get_btn", get_key_btn)
                keys.addWidget(get_key_btn)
                self._keys.append(get_key_btn)
        if not hasattr(self, f"_{service.id}_input"):
            keys.addStretch()
        details.addLayout(keys)

    def _prefer(self, category: str, service_id: str) -> None:
        """Search a service first for its type of media."""
        self._config.set(PREFERRED_KEYS[category], service_id)
        self.load()

    def _state(self, service) -> tuple[str, str | None]:
        """What the line of a service says, and its tone."""
        if service.auth_type in OAUTH_TYPES:
            session = self._config.get(
                service.session_key or f"{service.id}_session", ""
            )
            key = self._config.get(service.config_key, "") if service.config_key else ""
            if session and key:
                return tr("connected", "Connected"), "ok"
            if key:
                return tr("key_configured", "Key configured"), "ok"
            return tr("not_connected", "Not connected"), "info"
        if not service.config_key:
            return tr("settings_src_free", "Free"), "ok"
        if self._config.get_user_value(service.config_key, ""):
            return tr("settings_src_your_key", "Your key"), "ok"
        if self._config.get(service.config_key, ""):
            return tr("settings_src_builtin", "Built-in key"), "ok"
        return tr("settings_src_to_set_up", "To set up"), "info"

    def _usable(self, service) -> bool:
        """True if the service has what it needs to be searched."""
        if service.config_key and not self._config.get(service.config_key, ""):
            return False
        if service.requires_secret and not self._config.get(
            service.secret_config_key, ""
        ):
            return False
        return True

    def _save_key(self, config_key: str, input_field: QLineEdit) -> None:
        """Save the key typed in a field; an empty field removes the key."""
        value = input_field.text().strip()
        input_field.setText(value)
        if value == self._config.get_user_value(config_key, ""):
            return
        self._config.set(config_key, value)
        # The next search builds its API clients with the new key.
        reset_media_manager()
        self.load()

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
            reply = message_box.question(
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
        reply = message_box.question(
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

            self.load()

    def _on_auth_started(self, service: str):
        """Handle authentication started.

        Args:
            service: Service identifier.
        """
        status_lbl = getattr(self, f"_{service}_status", None)
        if status_lbl:
            status_lbl.setText(tr("connection_in_progress", "Connecting..."))
            set_tone(status_lbl, "warn")

    def _on_auth_success(self, service: str, data: dict):
        """Handle authentication success.

        Args:
            service: Service identifier.
            data: Authentication result data.
        """
        session_key = f"{service}_session"
        self._config.set(session_key, str(data))
        self.load()
        username = data.get("username", "")
        status_lbl = getattr(self, f"_{service}_status", None)
        if status_lbl is not None and username:
            status_lbl.setText(f"{tr('connected', 'Connected')} ({username})")
        message_box.information(
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
            set_tone(status_lbl, "error")
        message_box.warning(
            self,
            tr("connection_error", "Connection error"),
            f"{tr('connection_failed', 'Failed to connect:')}\n{error}",
        )

    def load(self):
        """Show the service searched first, and the state and key of each."""
        for category, line in self._first_lines.items():
            line.choice.set_value(self._config.get(PREFERRED_KEYS[category], ""))
        for service in get_all_services():
            row = self._rows.get(service.id)
            if row is None:
                continue
            text, tone = self._state(service)
            preferred_key = PREFERRED_KEYS.get(service.media_type)
            preferred = bool(
                preferred_key and self._config.get(preferred_key, "") == service.id
            )
            if preferred and not self._usable(service):
                tone = "warn"
            row.value.setText(text)
            set_tone(row.value, tone)

            input_field = getattr(self, f"_{service.id}_input", None)
            if input_field is not None:
                if service.id in SERVICES_WITH_DEFAULT_KEYS:
                    input_field.setPlaceholderText(
                        tr("custom_key_optional", "Custom key (Optional)...")
                    )
                    input_field.setToolTip(
                        tr(
                            "custom_key_tooltip",
                            "A key is already included. Enter a value only to use "
                            "your own key.",
                        )
                    )
                else:
                    input_field.setPlaceholderText(
                        tr("your_api_key", "Your API key...")
                    )
                input_field.setText(
                    self._config.get_user_value(service.config_key, "")
                    if service.config_key
                    else ""
                )
            if service.auth_type in OAUTH_TYPES:
                connected = tone == "ok"
                connect_btn = getattr(self, f"_{service.id}_connect_btn", None)
                disconnect_btn = getattr(self, f"_{service.id}_disconnect_btn", None)
                if connect_btn is not None:
                    connect_btn.setVisible(not connected)
                if disconnect_btn is not None:
                    disconnect_btn.setVisible(connected)

    def retranslate(self):
        """Update translatable UI text."""
        for label in [*self._api_cat_labels.values(), *self._abouts]:
            label.setText(tr(label.property("tr_key"), label.property("tr_default")))
        for key in self._keys:
            key.setText(tr(key.property("tr_key"), key.property("tr_default")))
        for line in self._first_lines.values():
            line.name.setText(tr("settings_src_first", "Searched first"))
        self.load()
