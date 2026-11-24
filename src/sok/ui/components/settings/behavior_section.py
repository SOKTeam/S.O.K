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

The file mode (move, hard link or copy) comes first, then one switch per
behavior: folder creation, posters, backups, duplicates, subtitles, log.
"""

from __future__ import annotations

from typing import Dict

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from sok.core.history import COPY, LINK, MOVE
from sok.ui.components.inputs import ModernComboBox
from sok.ui.components.settings.layout import Switch, SwitchLine, Lines
from sok.ui.i18n import tr
from sok.ui.theme import ui_font

FILE_MODE_LABELS = [
    (MOVE, "file_mode_move", "Move"),
    (LINK, "file_mode_link", "Hard link"),
    (COPY, "file_mode_copy", "Copy"),
]

# (translation key, default, setting) of each switch.
BEHAVIORS = [
    ("create_missing_folders", "Create missing folders", "create_folders"),
    ("download_posters", "Download posters", "download_posters"),
    ("backup_before_rename", "Backup before renaming", "backup_before_rename"),
    ("skip_duplicates", "Skip duplicates", "skip_duplicates"),
    ("subtitles_follow_video", "Move subtitles with videos", "subtitles_follow_video"),
    ("log_operations", "Log operations", "log_operations"),
]


class BehaviorSection(QWidget):
    """The file mode and the behaviors of a rename."""

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
        lines.add(self._create_file_mode_row())
        for _tr_key, _default, config_key in BEHAVIORS:
            line = SwitchLine()
            line.box.toggled.connect(
                lambda checked, k=config_key: self._config.set(k, checked)
            )
            self._toggles[config_key] = line.box
            self._lines[config_key] = line
            lines.add(line)

    def _create_file_mode_row(self) -> QWidget:
        """The file mode: its name, its combo, and what a hard link does."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.file_mode_lbl = QLabel()
        self.file_mode_lbl.setObjectName("SettingMuted")
        self.file_mode_lbl.setFont(ui_font(14))
        self.file_mode_combo = ModernComboBox()
        self.file_mode_combo.setMinimumWidth(160)
        self.file_mode_combo.setObjectName("SettingsCombo")
        for mode, _key, _default in FILE_MODE_LABELS:
            self.file_mode_combo.addItem("", mode)
        self.file_mode_combo.currentIndexChanged.connect(
            lambda index: self._config.set(
                "file_mode", self.file_mode_combo.itemData(index)
            )
        )
        layout.addWidget(self.file_mode_lbl)
        layout.addWidget(self.file_mode_combo)
        layout.addStretch()
        self._file_mode_hint = QLabel()
        self._file_mode_hint.setObjectName("SettingHint")
        self._file_mode_hint.setFont(ui_font(13))
        self._file_mode_hint.setWordWrap(True)
        box = QWidget()
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(0, 0, 0, 6)
        box_layout.setSpacing(6)
        box_layout.addWidget(row)
        box_layout.addWidget(self._file_mode_hint)
        return box

    def _translate_file_mode(self) -> None:
        self.file_mode_lbl.setText(tr("file_mode", "File mode"))
        self._file_mode_hint.setText(
            tr(
                "file_mode_hint",
                "A hard link leaves the original in place, so torrents keep "
                "seeding, without using more space. The destination must be on "
                "the same drive.",
            )
        )
        for i, (_mode, key, default) in enumerate(FILE_MODE_LABELS):
            self.file_mode_combo.setItemText(i, tr(key, default))

    def load(self):
        """Load settings values into UI."""
        for key, toggle in self._toggles.items():
            toggle.blockSignals(True)
            toggle.setChecked(self._config.get(key, False))
            toggle.blockSignals(False)
        mode = self._config.get("file_mode", MOVE)
        index = max(self.file_mode_combo.findData(mode), 0)
        self.file_mode_combo.blockSignals(True)
        self.file_mode_combo.setCurrentIndex(index)
        self.file_mode_combo.blockSignals(False)

    def retranslate(self):
        """Update translatable UI text."""
        self._translate_file_mode()
        for tr_key, default, config_key in BEHAVIORS:
            self._lines[config_key].label.setText(tr(tr_key, default))
        self.load()
