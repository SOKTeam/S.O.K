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
"""Page for TV shows: several series at once, each with its episodes.

The episodes dropped are grouped by series (the type detector of the home
page), each series is searched like a movie, then the seasons and the titles
of its episodes are loaded to name the files (the same engine as S.O.K
Server). The list shows a row per series and, under the selected one, its
episodes; the scene shows its poster and a square per episode of each season.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtWidgets import QWidget

from sok.core.batch import candidate_year, parse_series
from sok.core.interfaces import ContentType, MediaType
from sok.core.series import season_folders
from sok.file_operations import VideoFileOperations
from sok.file_operations.detection import detect_sources
from sok.media.video.series import Series
from sok.ui.components.organize.media_list import STATUS_OK, Entry
from sok.ui.components.organize.series_widgets import (
    EpisodeGrid,
    EpisodeLine,
    EpisodeLines,
    SeasonGrid,
)
from sok.ui.components.scene import Shape
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.i18n import tr, trn
from sok.ui.pages.batch_page import BatchPage
from sok.ui.workers import DetailsWorker


def group_by_series(files: List[Path]) -> List[List[Path]]:
    """One item per series, as the type detector groups the episodes.

    A file the detector does not see as an episode is an item of its own.
    """
    report = detect_sources(files)
    items: List[List[Path]] = []
    seen: set[Path] = set()
    for group in report.groups:
        mine = [f for f in group.files if f in files and f not in seen]
        if not mine:
            continue
        if group.kind == ContentType.EPISODE:
            items.append(mine)
        else:
            items.extend([f] for f in mine)
        seen.update(mine)
    items.extend([f] for f in files if f not in seen)
    return items


class SeriesPage(BatchPage):
    """Page for batch TV show renaming."""

    kind = "series"
    scene_shape = Shape.POSTER
    show_quality = True
    default_path_type = "video"
    media_type = MediaType.VIDEO
    content_type = ContentType.TV_SERIES
    factory_type = "tv"
    parse = staticmethod(parse_series)
    group_files = staticmethod(group_by_series)

    def __init__(self, parent: Optional[QWidget] = None):
        # Details of each series by id: seasons and episode titles.
        self._details: Dict[str, Dict[str, Any]] = {}
        self._details_queue: List[str] = []
        super().__init__(parent)
        self._details_runner = WorkerRunner(self)

    def make_ops(self) -> VideoFileOperations:
        return VideoFileOperations()

    def page_title(self) -> str:
        return tr("tv_shows", "TV Shows")

    def query_placeholder(self) -> str:
        return tr("batch_series_placeholder", "Series title")

    def stop_workers(self) -> None:
        super().stop_workers()
        self._details_runner.stop()

    # ----------------------------------------------------------- Details

    def _series_id(self, candidate: Optional[Dict[str, Any]]) -> Optional[str]:
        return (
            str(candidate["id"])
            if candidate and candidate.get("id") is not None
            else None
        )

    def _queue_details(self) -> None:
        """Load the details of the Ready series that do not have them yet."""
        for entry in self._list.entries():
            series_id = self._series_id(entry.candidate)
            if (
                entry.status == STATUS_OK
                and series_id
                and series_id not in self._details
                and series_id not in self._details_queue
            ):
                self._details_queue.append(series_id)
        self._next_details()

    def _next_details(self) -> None:
        if not self._details_queue or self._details_runner.is_running():
            return
        series_id = self._details_queue[0]
        worker = DetailsWorker(series_id, "tv", fetch_episodes=True)
        self._details_runner.run(
            worker,
            lambda details, s=series_id: self._on_details(s, details),
            lambda _err, s=series_id: self._on_details(s, {}),
        )

    def _on_details(self, series_id: str, details: Dict[str, Any]) -> None:
        if series_id in self._details_queue:
            self._details_queue.remove(series_id)
        self._details[series_id] = details or {"episodes": {}, "seasons": []}
        super()._refresh_previews_and_action()
        self._next_details()

    def _refresh_previews_and_action(self) -> None:
        self._queue_details()
        super()._refresh_previews_and_action()

    def _media_item(
        self, candidate: Optional[Dict[str, Any]], files: Optional[List[Path]] = None
    ) -> Any:
        """The series, with its episode titles and season folders once loaded."""
        series_id = self._series_id(candidate)
        details = self._details.get(series_id or "")
        if candidate and details:
            candidate = {**candidate, "episodes": details.get("episodes") or {}}
        item = super()._media_item(candidate, files)
        if isinstance(item, Series) and details:
            item.seasons = season_folders(details, tr("season", "Season"))
        return item

    # ------------------------------------------------------------- Names

    def _episode(self, file: Path) -> Tuple[Optional[int], Optional[int]]:
        info = self._ops.extract_info_from_filename(file.name)
        return info.get("season"), info.get("episode")

    def preview_name(self, item: Any, file: Path) -> str:
        """Season folder and new name, under the folder of the series."""
        series = item.get_folder_structure()[0]
        folder = self._ops.episode_folder(item, file.name, series, on_disk=False)
        return os.path.join(folder, self._ops.generate_new_filename(item, file.name))

    def organize_method(self) -> Callable[..., Dict[str, Any]]:
        """Organize each series on its own, then merge the reports."""

        def organize(mappings, dest_path, dry_run=False, progress_callback=None):
            by_series: Dict[int, Tuple[Any, List[Path]]] = {}
            for file, item in mappings:
                by_series.setdefault(id(item), (item, []))[1].append(file)
            merged: Dict[str, Any] = {
                "moved": [],
                "errors": [],
                "skipped": [],
                "subtitles": [],
                "total_files": 0,
                "total_moved": 0,
            }
            for item, files in by_series.values():
                report = self._ops.organize_files_list(
                    files,
                    dest_path,
                    item,
                    dry_run=dry_run,
                    progress_callback=progress_callback,
                )
                for key in ("moved", "errors", "skipped", "subtitles"):
                    merged[key].extend(report.get(key, []))
                merged["total_files"] += report.get("total_files", 0)
                merged["total_moved"] += report.get("total_moved", 0)
            return merged

        return organize

    # ---------------------------------------------------------- Display

    def _fields(self, entry: Entry, item: Any) -> List[Tuple[str, str]]:
        """No dotted sheet: the scene shows the seasons instead."""
        return []

    def count_of(self, entry: Entry) -> int:
        return len(entry.files)

    def lead_prefix(self, entries: List[Entry]) -> List[str]:
        if not entries:
            return []
        return [
            trn(
                "batch_series_count",
                len(entries),
                "Spread over {n} series.",
                "Spread over {n} series.",
            )
        ]

    def _seasons_note(self, entry: Entry) -> str:
        seasons = sorted(
            {s for s, _ in map(self._episode, entry.files) if s is not None}
        )
        episodes = trn(
            "batch_episodes", len(entry.files), "{n} episode", "{n} episodes"
        )
        if len(seasons) == 1:
            return f"{tr('season', 'Season')} {seasons[0]} · {episodes}"
        if seasons:
            count = trn("batch_seasons", len(seasons), "{n} season", "{n} seasons")
            return f"{count} · {episodes}"
        return episodes

    def _row_data(self, entry: Entry):
        data = super()._row_data(entry)
        if entry.status != "pending" and not data.unknown:
            data.note = self._seasons_note(entry)
            data.tags = []
        return data

    def row_detail(self, entry: Entry) -> Optional[QWidget]:
        item = self._media_item(entry.candidate)
        lines = []
        for file in sorted(entry.files, key=lambda f: (self._episode(f), f.name)):
            season, episode = self._episode(file)
            code = f"S{season:02d}E{episode:02d}" if season and episode else "—"
            title = ""
            if isinstance(item, Series) and code != "—":
                title = item.get_episode_info(code) or ""
            lines.append(EpisodeLine(code, title or file.stem, file.name))
        if not lines:
            return None
        more = len(lines) - 5
        return EpisodeLines(
            lines,
            tr("batch_was", "was"),
            trn(
                "batch_more_episodes",
                more,
                "+ {n} other episode",
                "+ {n} other episodes",
            ),
        )

    def _show_scene(self, key: Path) -> None:
        super()._show_scene(key)
        entry = self._list.entry(key)
        if entry is None:
            return
        item = self._media_item(entry.candidate)
        details = self._details.get(self._series_id(entry.candidate) or "")
        self._scene.set_extra(self._grid(entry, details) if item else None)

    def scene_subtitle(self, item: Any, candidate: Dict[str, Any]) -> str:
        year = candidate_year(candidate)
        label = tr("batch_series_label", "Series")
        return f"{label} · {year}" if year else label

    def scene_destination(self, entry: Entry) -> str:
        dest = self._dest_drop.get_path()
        if not dest or not entry.new_name:
            return ""
        return str(dest / os.path.dirname(entry.new_name)) + os.sep

    def _grid(
        self, entry: Entry, details: Optional[Dict[str, Any]]
    ) -> Optional[EpisodeGrid]:
        """A square per episode of each season among the files."""
        present: Dict[int, List[int]] = {}
        for file in entry.files:
            season, episode = self._episode(file)
            if season is not None and episode is not None:
                present.setdefault(season, []).append(episode)
        if not present:
            return None
        known = (details or {}).get("episodes") or {}
        grids = []
        for season in sorted(present)[:2]:
            prefix = f"S{season:02d}E"
            numbers = sorted(int(code[4:]) for code in known if code.startswith(prefix))
            if not numbers:
                numbers = sorted(set(present[season]))
            found = sum(1 for n in set(present[season]) if n in numbers)
            grids.append(
                SeasonGrid(
                    f"{tr('season', 'Season')} {season}",
                    trn(
                        "batch_episodes_found",
                        found,
                        "{n} episode found out of {total}",
                        "{n} episodes found out of {total}",
                    ).replace("{total}", str(len(numbers))),
                    numbers,
                    present[season],
                )
            )
        return EpisodeGrid(grids)
