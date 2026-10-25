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
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from PySide6.QtCore import Signal

from sok.core.batch import BatchMatcher, QueryParser, SameWork
from sok.core.interfaces import ContentType, MediaType
from sok.core.media_manager import get_media_manager
from sok.core.exceptions import APINotFoundError, UnsupportedMediaTypeError
from sok.core.history import content_kind, record
from sok.file_operations.artwork import save_artwork
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
        same_work: Optional[SameWork] = None,
        localized: bool = True,
        config=None,
    ):
        """Initialize the worker.

        Args:
            items: The files of each item to look up.
            media_type: Media type whose selected API is used.
            content_type: What to search, such as ContentType.MOVIE.
            parse: Reads the query and the year from the files of an item.
            query: Search text typed by the user, for a single item.
            same_work: Tells when several results are one work.
            localized: Ask for results in the language of the app. Left out
                for books, where it would hide books in other languages.
            config: Optional ConfigManager.
        """
        super().__init__(config)
        self._items = [list(item) for item in items]
        self._media_type = media_type
        self._content_type = content_type
        self._parse = parse
        self._query = query
        self._same_work = same_work
        self._localized = localized
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

        api_lang = None
        if self._localized:
            lang = self._config.get("language", "en")
            api_lang = f"{lang}-{lang.upper()}" if len(lang) == 2 else lang
        matcher = BatchMatcher(
            self._manager, self._content_type, self._parse, api_lang, self._same_work
        )

        if self._query is not None:
            return [await matcher.match(self._items[0], self._query)]

        def on_progress(done: int, total: int, file: Path) -> None:
            self.progress.emit(int((done / total) * 100) if total else 100, file.name)

        return await matcher.match_all(self._items, on_progress)


# Organizes (file, media item) pairs, such as organize_movies_batch().
OrganizeBatch = Callable[..., Dict[str, Any]]


class BatchOrganizeWorker(BaseWorker):
    """Worker that renames/moves files, each with its own media item.

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
        organize: OrganizeBatch,
        config=None,
    ):
        """Initialize the worker.

        Args:
            mappings: List of (file, media item) tuples.
            dest_path: Destination directory.
            organize: Method of the file operations that moves the files,
                such as VideoFileOperations.organize_movies_batch.
            config: Optional ConfigManager.
        """
        super().__init__(config)
        self._mappings = mappings
        self._dest = dest_path
        self._organize = organize

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
        with record(content_kind(self._mappings[0][1])) as journal:
            report = self._organize(
                mappings=self._mappings,
                dest_path=str(self._dest),
                dry_run=False,
                progress_callback=self._on_progress,
            )
            if self._config.get("download_posters") and report.get("moved"):
                self.progress.emit(100, "Downloading posters...")
                save_artwork(self._mappings, report["moved"], str(self._dest))
        self.progress.emit(100, "Done!")
        self.finished.emit(
            {
                "total": report.get("total_files", 0),
                "success": report.get("total_moved", 0),
                "moved": report.get("moved", []),
                "subtitles": len(report.get("subtitles", [])),
                "errors": report.get("errors", []),
                "skipped": report.get("skipped", []),
                "operation": journal.operation_id,
            }
        )
