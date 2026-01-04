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
Folder Creation Worker for structural organization.
"""

import os
import logging
from PySide6.QtCore import Signal
from sok.ui.workers.base import BaseWorker
from sok.core.utils import format_name

logger = logging.getLogger(__name__)


class CreateFoldersWorker(BaseWorker):
    """Worker for creating directory structures.

    Creates series and season folders for media organization.

    Signals:
        progress (int, str): Percent complete and status message.
        finished (dict): Report with total, created count, and errors.
    """

    progress = Signal(int, str)
    finished = Signal(dict)

    def __init__(self, dest_path: str, series_title: str, seasons: dict, config=None):
        """Initialize the folder creation worker.

        Args:
            dest_path: Base destination directory path.
            series_title: Name of the series for the root folder.
            seasons: Dict mapping season names to numbers.
            config: Configuration manager (uses default if None).
        """
        super().__init__(config)
        self._dest_path = dest_path
        self._series_title = series_title
        self._seasons = seasons

    def execute(self):
        """Execute folder creation.

        Creates series folder and season subfolders.
        """
        total = len(self._seasons) + 1
        created, errors = [], []

        self.progress.emit(0, f"Creating folder: {self._series_title}")
        series_path = os.path.join(self._dest_path, format_name(self._series_title))

        if not os.path.exists(series_path):
            os.makedirs(series_path, exist_ok=True)
            created.append(series_path)

        for idx, (season_name, season_num) in enumerate(self._seasons.items(), start=1):
            percent = int((idx / total) * 100)
            self.progress.emit(percent, f"Creating: {season_name}")

            season_path = os.path.join(series_path, format_name(season_name))
            try:
                if not os.path.exists(season_path):
                    os.makedirs(season_path, exist_ok=True)
                    created.append(season_path)
            except OSError as exc:
                logger.exception(
                    "Failed to create season folder %s", season_path, exc_info=exc
                )
                errors.append({"folder": season_name, "error": str(exc)})

        self.progress.emit(100, "Done!")
        self.finished.emit(
            {
                "total": total,
                "created": len(created),
                "errors": errors,
                "series_path": series_path,
            }
        )
