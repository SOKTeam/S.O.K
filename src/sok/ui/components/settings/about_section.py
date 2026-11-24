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

The version in Geist Mono, a switch for the update check and one for Discord,
and the key that resets every setting.
"""

from typing import Dict

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from sok.__version__ import __version__
from sok.ui import message_box
from sok.ui.components.base import KeyButton
from sok.ui.components.settings.layout import Switch, SwitchLine, Lines
from sok.ui.i18n import tr
from sok.ui.theme import ui_font

# (translation key, default, setting) of each switch.
OPTIONS = [
    ("check_updates", "Check for updates", "check_updates"),
    ("discord_rpc", "Discord Rich Presence", "use_discord_rpc"),
]


class AboutSection(QWidget):
    """Version, update check, Discord, and the reset key.

    Signals:
        reset_requested: The user confirmed the reset of the settings.
    """

    reset_requested = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._toggles: Dict[str, Switch] = {}
        self._lines: Dict[str, SwitchLine] = {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lines = Lines()
        layout.addWidget(lines)

        version = QWidget()
        version_layout = QHBoxLayout(version)
        version_layout.setContentsMargins(0, 0, 0, 0)
        version_layout.setSpacing(12)
        self._version_lbl = QLabel()
        self._version_lbl.setObjectName("SettingMuted")
        self._version_lbl.setFont(ui_font(14))
        self._version_lbl.setFixedWidth(86)
        number = QLabel(__version__)
        number.setObjectName("SettingPath")
        number.setFont(ui_font(13, 400, mono=True))
        version_layout.addWidget(self._version_lbl)
        version_layout.addWidget(number, 1)
        lines.add(version)

        for _tr_key, _default, config_key in OPTIONS:
            line = SwitchLine()
            line.box.toggled.connect(
                lambda checked, k=config_key: self._config.set(k, checked)
            )
            self._toggles[config_key] = line.box
            self._lines[config_key] = line
            lines.add(line)

        reset = QHBoxLayout()
        reset.setContentsMargins(0, 6, 0, 0)
        self.reset_btn = KeyButton("", small=True)
        self.reset_btn.set_danger(True)
        self.reset_btn.clicked.connect(self._confirm_reset)
        reset.addWidget(self.reset_btn)
        reset.addStretch()
        holder = QWidget()
        holder.setLayout(reset)
        lines.add(holder)

    def _confirm_reset(self):
        """Ask before resetting every setting."""
        reply = message_box.question(
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
        self._version_lbl.setText(tr("version", "Version"))
        self.reset_btn.setText(tr("reset_settings", "Reset settings"))
        for tr_key, default, config_key in OPTIONS:
            self._lines[config_key].label.setText(tr(tr_key, default))
        self.load()
