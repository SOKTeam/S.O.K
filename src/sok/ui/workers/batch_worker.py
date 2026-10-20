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
"""Workers for batch search and organization."""

import logging
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

from PySide6.QtCore import Signal

from sok.core.batch import BatchMatcher, QueryParser
from sok.core.interfaces import ContentType, MediaType
from sok.core.media_manager import get_media_manager
from sok.core.exceptions import APINotFoundError, UnsupportedMediaTypeError
from sok.file_operations.video_operations import VideoFileOperations
from sok.ui.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class BatchSearchWorker(BaseWorker):
    """Worker that searches the online database once per item of a batch.

    Signals:
        progress (int, str): Percent complete and current filename.
        finished (list): One sok.core.batch.BatchMatch per item, in order.
    """

    progress = Signal(int, str)
    finished = Signal(list)

    def __init__(
        self,
        items: Sequence[Sequence[Path]],
        media_type: MediaType,
        content_type: ContentType,
        parse: QueryParser,
        query: Optional[str] = None,
        config=None,
    ):
        """Initialize the worker.

        Args:
            items: The files of each item to look up.
            media_type: Media type whose selected API is used.
            content_type: What to search, such as ContentType.MOVIE.
            parse: Reads the query and the year from the files of an item.
            query: Search text typed by the user, for a single item.
            config: Optional ConfigManager.
        """
        super().__init__(config)
        self._items = [list(item) for item in items]
        self._media_type = media_type
        self._content_type = content_type
        self._parse = parse
        self._query = query
        self._manager = get_media_manager()

    def execute(self):
        """Run the async batch search."""
        if not self._loop:
            return
        results = self._loop.run_until_complete(self._search_all())
        self.finished.emit(results)

    async def _search_all(self) -> list:
        """Search every item with the batch matcher."""
        try:
            self._manager.get_current_api(self._media_type)
        except (UnsupportedMediaTypeError, APINotFoundError) as exc:
            logger.error("No %s API configured", self._media_type.value, exc_info=exc)
            raise RuntimeError(
                f"No API configured for {self._media_type.value}."
            ) from exc

        lang = self._config.get("language", "en")
        api_lang = f"{lang}-{lang.upper()}" if len(lang) == 2 else lang
        matcher = BatchMatcher(self._manager, self._content_type, self._parse, api_lang)

        if self._query is not None:
            return [await matcher.match(self._items[0], self._query)]

        def on_progress(done: int, total: int, file: Path) -> None:
            self.progress.emit(int((done / total) * 100) if total else 100, file.name)

        return await matcher.match_all(self._items, on_progress)


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
