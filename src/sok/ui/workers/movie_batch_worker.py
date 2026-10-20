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
"""Workers for batch movie search and organization."""

import logging
from pathlib import Path
from typing import Any, List, Optional, Tuple

from PySide6.QtCore import Signal

from sok.core.batch import BatchMatcher, parse_movie
from sok.core.interfaces import ContentType, MediaType
from sok.core.media_manager import get_media_manager
from sok.core.exceptions import APINotFoundError, UnsupportedMediaTypeError
from sok.file_operations.video_operations import VideoFileOperations
from sok.ui.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class MovieBatchSearchWorker(BaseWorker):
    """Worker that searches the video database once per file.

    Signals:
        progress (int, str): Percent complete and current filename.
        finished (list): One sok.core.batch.BatchMatch per file, in order.
    """

    progress = Signal(int, str)
    finished = Signal(list)

    def __init__(self, files: List[Path], query: Optional[str] = None, config=None):
        """Initialize the worker.

        Args:
            files: Video files to look up.
            query: Search text typed by the user, for a single file.
            config: Optional ConfigManager.
        """
        super().__init__(config)
        self._files = files
        self._query = query
        self._manager = get_media_manager()

    def execute(self):
        """Run the async batch search."""
        if not self._loop:
            return
        results = self._loop.run_until_complete(self._search_all())
        self.finished.emit(results)

    async def _search_all(self) -> list:
        """Search every file with the batch matcher."""
        try:
            self._manager.get_current_api(MediaType.VIDEO)
        except (UnsupportedMediaTypeError, APINotFoundError) as exc:
            logger.error("No video API configured", exc_info=exc)
            raise RuntimeError("No API configured for video.") from exc

        lang = self._config.get("language", "en")
        api_lang = f"{lang}-{lang.upper()}" if len(lang) == 2 else lang
        matcher = BatchMatcher(self._manager, ContentType.MOVIE, parse_movie, api_lang)

        if self._query is not None:
            return [await matcher.match(self._files, self._query)]

        def on_progress(done: int, total: int, file: Path) -> None:
            self.progress.emit(int((done / total) * 100) if total else 100, file.name)

        return await matcher.match_all([[f] for f in self._files], on_progress)


class MovieBatchOrganizeWorker(BaseWorker):
    """Worker that renames/moves a list of movies, each with its own metadata.

    Signals:
        progress (int, str): Percent complete and current filename.
        finished (dict): Report with total/success/errors/skipped.
    """

    progress = Signal(int, str)
    finished = Signal(dict)

    def __init__(
        self,
        mappings: List[Tuple[Path, Any]],
        dest_path: str,
        ops: VideoFileOperations,
        config=None,
    ):
        """Initialize the worker.

        Args:
            mappings: List of (file, Movie) tuples.
            dest_path: Destination directory.
            ops: VideoFileOperations instance.
            config: Optional ConfigManager.
        """
        super().__init__(config)
        self._mappings = mappings
        self._dest = dest_path
        self._ops = ops

    def _on_progress(self, current: int, total: int, filename: str):
        if total > 0:
            pct = int((current / total) * 100)
            self.progress.emit(pct, f"({current}/{total}) {filename}")

    def execute(self):
        """Execute the batch rename."""
        if not self._mappings:
            self.finished.emit({"total": 0, "success": 0, "errors": [], "skipped": []})
            return

        self.progress.emit(0, "Preparing...")
        report = self._ops.organize_movies_batch(
            mappings=self._mappings,
            dest_path=str(self._dest),
            dry_run=False,
            progress_callback=self._on_progress,
        )
        self.progress.emit(100, "Done!")
        self.finished.emit(
            {
                "total": report.get("total_files", 0),
                "success": report.get("total_moved", 0),
                "moved": report.get("moved", []),
                "errors": report.get("errors", []),
                "skipped": report.get("skipped", []),
            }
        )
