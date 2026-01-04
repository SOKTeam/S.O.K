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
Organize Worker for file moving and renaming.
"""

from pathlib import Path
from typing import List
from PySide6.QtCore import Signal
from sok.ui.workers.base import BaseWorker


class OrganizeWorker(BaseWorker):
    """Worker for file organization operations.

    Moves and renames files in a background thread.

    Signals:
        progress (int, str): Percent complete and status message.
        finished (dict): Final report with total, success, errors.
    """

    progress = Signal(int, str)
    finished = Signal(dict)

    def __init__(
        self, files: List[Path], dest: Path | None, media_item, ops, config=None
    ):
        """Initialize the organize worker.

        Args:
            files: List of source file paths.
            dest: Destination directory path.
            media_item: Media item for naming templates.
            ops: File operations handler instance.
            config: Configuration manager (uses default if None).
        """
        super().__init__(config)
        self._files = files
        self._dest = dest
        self._media_item = media_item
        self._ops = ops

    def _on_progress(self, current: int, total: int, filename: str):
        """Handle progress updates from file operations.

        Args:
            current: Number of files processed.
            total: Total number of files.
            filename: Current file being processed.
        """
        if total > 0:
            percent = int((current / total) * 100)
            self.progress.emit(percent, f"({current}/{total}) {filename}")

    def execute(self):
        """Execute file organization.

        Moves and renames files, emitting progress and final report.
        """
        if not self._files:
            self.finished.emit({"total": 0, "success": 0, "errors": []})
            return

        self.progress.emit(0, "Analyzing files...")

        report = self._ops.organize_files_list(
            files=self._files,
            dest_path=str(self._dest),
            media_item=self._media_item,
            dry_run=False,
            progress_callback=self._on_progress,
        )

        self.progress.emit(100, "Done!")
        self.finished.emit(
            {
                "total": report.get("total_files", 0),
                "success": report.get("total_moved", 0),
                "errors": report.get("errors", []),
            }
        )
