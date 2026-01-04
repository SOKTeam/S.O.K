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
"""About section for settings page.

Displays application version, update settings, Discord RPC toggle,
and provides a reset settings button.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QMessageBox,
    QSizePolicy,
)
from sok.__version__ import __version__
from sok.ui.components.base import Card, Row, ActionButton, Toggle
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.i18n import tr
from sok.ui.theme import card_shadow


class AboutSection(QWidget):
    """About and global actions section.

    Displays application version, update settings, Discord RPC toggle,
    and provides a reset settings button.

    Signals:
        reset_requested: Emitted when user confirms settings reset.
    """

    reset_requested = Signal()

    def __init__(self, config, parent=None):
        """Initialize the about section.

        Args:
            config: Configuration manager instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._config = config
        self._toggles = {}
        self._build()

    def _build(self):
        """Build the section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = make_section_label("about", "ABOUT")
        layout.addWidget(self.label)

        card = Card()

        self.version_row = Row("")
        self.version_row.setProperty("tr_key", "version")
        self.version_row.setProperty("tr_default", "Version")
        self.version_row.set_value(__version__)
        self.version_row.set_chevron(False)
        card.add(self.version_row)

        for tr_key, default, config_key in [
            ("check_updates", "Check for updates", "check_updates"),
            ("discord_rpc", "Discord Rich Presence", "use_discord_rpc"),
        ]:
            card.add(self._create_toggle_row(tr_key, default, config_key))

        reset_row = QWidget()
        reset_row.setFixedHeight(44)
        rr_layout = QHBoxLayout(reset_row)
        rr_layout.setContentsMargins(12, 6, 12, 6)

        self.reset_btn = ActionButton("")
        self.reset_btn.setProperty("tr_key", "reset_settings")
        self.reset_btn.setProperty("tr_default", "Reset settings")
        self.reset_btn.clicked.connect(self._confirm_reset)
        rr_layout.addWidget(self.reset_btn)

        card.add(reset_row)

        card.setGraphicsEffect(card_shadow())
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(card)

    def _create_toggle_row(self, tr_key: str, default: str, config_key: str) -> QWidget:
        """Create a row with a label and toggle.

        Args:
            tr_key: Translation key for the label.
            default: Default label text.
            config_key: Configuration key for the toggle.

        Returns:
            Widget containing the row.
        """
        row = QWidget()
        row.setFixedHeight(32)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 0, 12, 0)

        title_lbl = QLabel()
        title_lbl.setProperty("tr_key", tr_key)
        title_lbl.setProperty("tr_default", default)
        title_lbl.setObjectName("RowTitle")

        toggle = Toggle()
        toggle.setProperty("config_key", config_key)
        toggle.toggled.connect(lambda checked: self._config.set(config_key, checked))
        self._toggles[config_key] = toggle

        layout.addWidget(title_lbl)
        layout.addStretch()
        layout.addWidget(toggle)
        return row

    def _confirm_reset(self):
        """Show reset confirmation dialog."""
        reply = QMessageBox.question(
            self,
            tr("reset_title", "Reset"),
            tr("reset_confirm", "Are you sure you want to reset all settings?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.reset_requested.emit()

    def load(self):
        """Load settings values into UI."""
        for key, toggle in self._toggles.items():
            toggle.blockSignals(True)
            toggle.setChecked(self._config.get(key, False))
            toggle.blockSignals(False)

    def retranslate(self):
        """Update translatable UI text."""
        self.label.setText(tr("about", "ABOUT"))
        self.version_row.set_title(tr("version", "Version"))
        self.reset_btn.setText(tr("reset_settings", "Reset settings"))
        for toggle in self._toggles.values():
            lbl = toggle.parentWidget().findChild(QLabel)
            if lbl:
                tr_key = lbl.property("tr_key")
                default = lbl.property("tr_default")
                lbl.setText(tr(tr_key, default or ""))
        self.load()
