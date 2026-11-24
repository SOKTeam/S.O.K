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
"""Music page: albums and loose tracks, several at once.

The audio files dropped are grouped like on the home page: the tracks of an
album folder make one item, searched as an album; a track on its own is an
item searched as a track (the same engine as S.O.K Server). The scene shows
the cover and the tracks of the album, with their length.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtWidgets import QWidget

from sok.core.batch import (
    candidate_year,
    parse_album,
    parse_track,
    same_album,
    same_track,
)
from sok.core.interfaces import ContentType, MediaType
from sok.file_operations import MusicFileOperations
from sok.file_operations.detection import detect_sources
from sok.ui.components.organize.media_list import Entry
from sok.ui.components.organize.track_list import TrackLine, TrackList
from sok.ui.components.scene import Shape
from sok.ui.i18n import tr, trn
from sok.ui.pages.batch_page import BatchPage, SearchSpec

ALBUM = SearchSpec(ContentType.ALBUM, parse_album, same_album, False, "album")
TRACK = SearchSpec(ContentType.TRACK, parse_track, same_track, False, "track")


def describe_track(candidate: Dict[str, Any]) -> str:
    """ "Title — Artist (Album, year)", the text of a result."""
    title = candidate.get("title") or tr("unknown", "Unknown")
    text = f"{title} — {candidate['artist']}" if candidate.get("artist") else title
    details = [str(v) for v in (candidate.get("album"), candidate_year(candidate)) if v]
    return f"{text} ({', '.join(details)})" if details else text


def length_text(seconds: Optional[float]) -> str:
    """ "5:20" for a length in seconds, "" when unknown."""
    if not seconds:
        return ""
    minutes, rest = divmod(int(round(seconds)), 60)
    return f"{minutes}:{rest:02d}"


class MusicPage(BatchPage):
    """Page for batch music renaming: albums and loose tracks."""

    kind = "music"
    scene_shape = Shape.COVER
    default_path_type = "music"
    media_type = MediaType.MUSIC
    content_type = ContentType.TRACK
    factory_type = "track"
    parse = staticmethod(parse_track)
    same_work = staticmethod(same_track)
    localized = False
    describe = staticmethod(describe_track)

    def __init__(self, parent: Optional[QWidget] = None):
        # Key of every item that is an album.
        self._albums: set[Path] = set()
        self._tags: Dict[Path, Dict[str, Any]] = {}
        super().__init__(parent)

    def make_ops(self) -> MusicFileOperations:
        return MusicFileOperations()

    def organize_method(self) -> Callable[..., Dict[str, Any]]:
        return self._ops.organize_items_batch

    def page_title(self) -> str:
        return tr("music", "Music")

    def query_placeholder(self) -> str:
        return tr("batch_music_placeholder", "Album or title (optional artist)")

    # ------------------------------------------------------------- Items

    def group_files(self, files: List[Path]) -> List[List[Path]]:  # type: ignore[override]
        """An item per album folder, and one per track on its own."""
        report = detect_sources(files)
        items: List[List[Path]] = []
        seen: set[Path] = set()
        for group in report.groups:
            mine = [f for f in group.files if f in files and f not in seen]
            if not mine:
                continue
            if group.kind == ContentType.ALBUM:
                items.append(mine)
                self._albums.add(mine[0])
            else:
                items.extend([f] for f in mine)
            seen.update(mine)
        items.extend([f] for f in files if f not in seen)
        return items

    def search_spec(self, files: Optional[List[Path]] = None) -> SearchSpec:
        return ALBUM if files and files[0] in self._albums else TRACK

    def _is_album(self, entry: Entry) -> bool:
        return entry.key in self._albums

    def _tags_of(self, file: Path) -> Dict[str, Any]:
        if file not in self._tags:
            try:
                self._tags[file] = self._ops.read_metadata(str(file)) or {}
            except (OSError, ValueError):
                self._tags[file] = {}
        return self._tags[file]

    def preview_name(self, item: Any, file: Path) -> str:
        folders, name = self._ops.batch_target(item, file, True)
        return "/".join([*folders, name])

    # ---------------------------------------------------------- Display

    def count_of(self, entry: Entry) -> int:
        return len(entry.files)

    def lead_prefix(self, entries: List[Entry]) -> List[str]:
        albums = sum(1 for e in entries if self._is_album(e))
        if not albums:
            return []
        return [trn("batch_album_count", albums, "In {n} album.", "In {n} albums.")]

    def _fields(self, entry: Entry, item: Any) -> List[Tuple[str, str]]:
        """No dotted sheet: the scene lists the tracks instead."""
        return []

    def _row_data(self, entry: Entry):
        data = super()._row_data(entry)
        if entry.status == "pending" or data.unknown:
            if self._is_album(entry):
                data.note = trn(
                    "batch_tracks", len(entry.files), "{n} track", "{n} tracks"
                )
            return data
        item = self._media_item(entry.candidate, entry.files)
        artist = self.item_author(item)
        if self._is_album(entry):
            data.note = " · ".join(x for x in (artist, data.year) if x)
        else:
            album = getattr(item, "album", "") or ""
            data.note = " · ".join(x for x in (artist, album) if x)
        data.by, data.year = "", ""
        return data

    def scene_subtitle(self, item: Any, candidate: Dict[str, Any]) -> str:
        entry = self._list.entry(self._list.current())
        year = getattr(item, "year", None) or candidate_year(candidate)
        parts = [self.item_author(item), str(year or "")]
        if entry is not None and self._is_album(entry):
            parts.append(
                trn("batch_tracks", len(entry.files), "{n} track", "{n} tracks")
            )
        else:
            parts[1] = getattr(item, "album", "") or parts[1]
        return " · ".join(p for p in parts if p)

    def scene_destination(self, entry: Entry) -> str:
        dest = self._dest_drop.get_path()
        if not dest or not entry.new_name:
            return ""
        if self._is_album(entry):
            return str(dest / os.path.dirname(entry.new_name)) + os.sep
        return str(dest / entry.new_name)

    def _show_scene(self, key: Path) -> None:
        super()._show_scene(key)
        entry = self._list.entry(key)
        if entry is None or not self._is_album(entry) or entry.candidate is None:
            self._scene.set_extra(None)
            return
        lines = []
        for index, file in enumerate(sorted(entry.files), start=1):
            tags = self._tags_of(file)
            info = self._ops.extract_info_from_filename(file.name)
            raw = str(tags.get("track_number") or info.get("track_number") or index)
            digits = raw.split("/")[0].strip()
            number = int(digits) if digits.isdigit() else index
            title = tags.get("title") or info.get("title") or file.stem
            lines.append(
                TrackLine(f"{number:02d}", title, length_text(tags.get("duration")))
            )
        more = len(lines) - 6
        self._scene.set_extra(
            TrackList(
                lines, trn("batch_more_tracks", more, "+ {n} track", "+ {n} tracks")
            )
        )
