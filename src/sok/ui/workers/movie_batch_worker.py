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

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PySide6.QtCore import Signal

from sok.core.interfaces import ContentType, MediaType
from sok.core.media_manager import get_media_manager
from sok.core.exceptions import APIError, APINotFoundError, UnsupportedMediaTypeError
from sok.file_operations.video_operations import VideoFileOperations
from sok.ui.workers.base import BaseWorker

logger = logging.getLogger(__name__)

MAX_CANDIDATES_PER_FILE = 5
SEARCH_CONCURRENCY = 4


class MovieBatchSearchWorker(BaseWorker):
    """Worker that queries TMDB once per file to find movie candidates.

    Signals:
        progress (int, str): Percent complete and current filename.
        finished (list): List of per-file result dicts with keys:
            file (Path), query (str), year (int|None), candidates (list[dict]).
    """

    progress = Signal(int, str)
    finished = Signal(list)

    def __init__(self, files: List[Path], config=None):
        """Initialize the worker.

        Args:
            files: Video files to look up.
            config: Optional ConfigManager.
        """
        super().__init__(config)
        self._files = files
        self._ops = VideoFileOperations()
        self._manager = get_media_manager()

    def execute(self):
        """Run the async batch search."""
        if not self._loop:
            return
        results = self._loop.run_until_complete(self._search_all())
        self.finished.emit(results)

    async def _search_all(self) -> List[Dict[str, Any]]:
        """Search every file in parallel with a concurrency cap."""
        try:
            self._manager.get_current_api(MediaType.VIDEO)
        except (UnsupportedMediaTypeError, APINotFoundError) as exc:
            logger.error("No video API configured", exc_info=exc)
            raise RuntimeError("No API configured for video.") from exc

        lang = self._config.get("language", "en")
        api_lang = f"{lang}-{lang.upper()}" if len(lang) == 2 else lang

        semaphore = asyncio.Semaphore(SEARCH_CONCURRENCY)
        total = len(self._files)
        done = 0
        lock = asyncio.Lock()

        async def run_one(idx: int, file: Path) -> Dict[str, Any]:
            nonlocal done
            async with semaphore:
                result = await self._search_one(file, api_lang)
            async with lock:
                done += 1
                pct = int((done / total) * 100) if total else 100
                self.progress.emit(pct, file.name)
            return result

        tasks = [run_one(i, f) for i, f in enumerate(self._files)]
        return await asyncio.gather(*tasks)

    async def _search_one(self, file: Path, api_lang: str) -> Dict[str, Any]:
        """Search TMDB for a single file's title guess."""
        info = self._ops.extract_info_from_filename(file.name)
        title = info.get("title") or Path(file.stem).name
        year = info.get("year")

        candidates: List[Dict[str, Any]] = []
        try:
            result = await self._manager.search(
                title, ContentType.MOVIE, language=api_lang
            )
            raw = (
                result.get("results", []) if isinstance(result, dict) else result or []
            )
            candidates = list(raw)[:MAX_CANDIDATES_PER_FILE]
        except APIError as exc:
            logger.warning("Search failed for %s: %s", file.name, exc)

        return {
            "file": file,
            "query": title,
            "year": year,
            "candidates": candidates,
        }


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
                "errors": report.get("errors", []),
                "skipped": report.get("skipped", []),
            }
        )
