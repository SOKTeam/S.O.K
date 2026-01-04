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
Options widget for the organization page.

Manages source/destination drop zones and action controls.
"""

import logging
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Signal

from sok.ui.theme import card_shadow
from sok.ui.components.base import ActionButton
from sok.ui.components.inputs import DropZone
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.controllers.ui_state import set_progress
from sok.ui.i18n import tr

logger = logging.getLogger(__name__)


class OptionsPanel(QWidget):
    """
    Options panel for the organization page.

    This component manages action controls and path selection:
    - Drop zone for source folders (multi-selection)
    - Drop zone for destination folder
    - Progress bar with message
    - Main action button ("Organize files")
    - Folder creation button (TV series only)

    Attributes:
        _media_type (str): Media type ('video', 'music', 'book', 'game')
        _source_drop (DropZone): Source drop zone
        _dest_drop (DropZone): Destination drop zone
        _action_btn (ActionButton): Main action button
        _create_folders_btn (ActionButton): Folder creation button (TV)

    Signals:
        source_changed(list[Path]): Emitted when source folders change.
            - list: List of Path objects for selected folders
        destination_changed(str): Emitted when destination changes.
            - str: Absolute path of the destination folder
        organize_clicked(): Emitted when the organize button is clicked.
        create_folders_clicked(): Emitted when the folder creation
            button is clicked (TV series only).

    Example:
        >>> panel = OptionsPanel("video")
        >>> panel.source_changed.connect(lambda paths: scan_files(paths))
        >>> panel.organize_clicked.connect(start_organization)
        >>> panel.set_progress(True, "Organizing...", 50)
    """

    source_changed = Signal(list)
    destination_changed = Signal(str)
    organize_clicked = Signal()
    create_folders_clicked = Signal()

    def __init__(self, media_type: str, parent: Optional[QWidget] = None):
        """Initialize the options panel.

        Args:
            media_type: Type of media ('video', 'music', 'book', 'game').
            parent: Parent widget.
        """
        super().__init__(parent)
        self._media_type = media_type
        self._build_ui()

    def _build_ui(self):
        """Builds the options panel interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._create_folders_btn = ActionButton("")
        self._create_folders_btn.setEnabled(False)
        self._create_folders_btn.setVisible(False)
        self._create_folders_btn.clicked.connect(self.create_folders_clicked.emit)
        layout.addWidget(self._create_folders_btn)

        self._lbl_source = make_section_label("source_folders", "SOURCE FOLDERS")
        layout.addWidget(self._lbl_source)

        self._source_drop = DropZone(multi_select=True)
        self._source_drop.files_dropped.connect(self._on_source_dropped)
        self._source_drop.setGraphicsEffect(card_shadow())
        layout.addWidget(self._source_drop)

        self._lbl_destination = make_section_label("destination", "DESTINATION")
        layout.addWidget(self._lbl_destination)

        self._dest_drop = DropZone()
        self._dest_drop.files_dropped.connect(self._on_dest_dropped)
        self._dest_drop.setGraphicsEffect(card_shadow())
        layout.addWidget(self._dest_drop)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(6)
        self._progress.setVisible(False)
        self._progress.setTextVisible(False)
        self._progress.setObjectName("Progress")
        layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("EmptyState")
        self._progress_label.setVisible(False)
        layout.addWidget(self._progress_label)

        self._action_btn = ActionButton("")
        self._action_btn.setEnabled(False)
        self._action_btn.clicked.connect(self.organize_clicked.emit)
        layout.addWidget(self._action_btn)

    def _on_source_dropped(self, paths: List[Path]):
        """Handle files dropped in the source zone.

        Args:
            paths: List of dropped folder paths.
        """
        self.source_changed.emit(paths)

    def _on_dest_dropped(self, paths: List[Path]):
        """Handle files dropped in the destination zone.

        Args:
            paths: List of dropped folder paths (only first used).
        """
        self.destination_changed.emit(self._dest_drop.get_path())

    def get_destination_path(self) -> Path | None:
        """Get the selected destination path.

        Returns:
            Destination path or None if not set.
        """
        return self._dest_drop.get_path()

    def has_valid_destination(self) -> bool:
        """Check if the destination is valid.

        Returns:
            True if destination exists.
        """
        dest_path = self._dest_drop.get_path()
        return dest_path is not None and Path(dest_path).exists()

    def set_progress(
        self, visible: bool, message: Optional[str] = None, value: Optional[int] = None
    ) -> None:
        """
        Updates the progress display.

        Args:
            visible: True to show the bar and message, False to hide.
            message: Text to display under the bar (e.g., "Organizing...").
            value: Progress percentage (0-100). None for indeterminate mode.
        """
        set_progress(self._progress, self._progress_label, visible, message, value)

    def set_action_enabled(self, enabled: bool):
        """Enable or disable the action button.

        Args:
            enabled: Whether to enable the button.
        """
        self._action_btn.setEnabled(enabled)

    def update_action_state(self, has_files: bool, has_media: bool) -> None:
        """
        Updates the action button state according to context.

        Args:
            has_files: True if files are selected in sources.
            has_media: True if a media is selected (for videos).

        Logic:
            - For videos: requires files + destination + selected media
            - For other types: requires files + destination only
        """
        has_dest = self.has_valid_destination()

        if self._media_type == "video":
            self._action_btn.setEnabled(has_files and has_dest and has_media)
        else:
            self._action_btn.setEnabled(has_files and has_dest)

    def update_create_folders_visibility(self, content_type: str, has_media: bool):
        """Update the visibility of the create folders button.

        Args:
            content_type: Content type ('tv' or 'movie').
            has_media: Whether a media is selected.
        """
        is_tv = content_type == "tv" and has_media
        self._create_folders_btn.setVisible(is_tv)
        self._create_folders_btn.setEnabled(is_tv and self.has_valid_destination())

    def set_create_folders_enabled(self, enabled: bool):
        """Enable or disable the create folders button.

        Args:
            enabled: Whether to enable the button.
        """
        self._create_folders_btn.setEnabled(enabled)

    def set_create_folders_text(self, text: str):
        """Set the text of the create folders button.

        Args:
            text: Button text.
        """
        self._create_folders_btn.setText(text)

    def retranslate_ui(self):
        """Updates texts after a language change."""
        self._lbl_source.setText(tr("source_folders", "SOURCE FOLDERS"))
        self._lbl_destination.setText(tr("destination", "DESTINATION"))
        self._action_btn.setText(tr("organize_action", "Organize files"))
        self._create_folders_btn.setText(
            tr("create_series_folders", "Create series folders")
        )
