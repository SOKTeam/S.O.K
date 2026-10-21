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
"""Page for batch-renaming tracks, each with its own online track."""

from pathlib import Path
from typing import Any, Callable, Dict

from sok.core.batch import candidate_year, parse_track, same_track
from sok.core.interfaces import ContentType, MediaType
from sok.file_operations import MusicFileOperations
from sok.ui.i18n import tr
from sok.ui.pages.batch_page import BatchPage


def describe_track(candidate: Dict[str, Any]) -> str:
    """ "Title — Artist (Album, year)", the text of a track in the menu."""
    title = candidate.get("title") or tr("unknown", "Unknown")
    text = f"{title} — {candidate['artist']}" if candidate.get("artist") else title
    details = [str(v) for v in (candidate.get("album"), candidate_year(candidate)) if v]
    return f"{text} ({', '.join(details)})" if details else text


class TracksPage(BatchPage):
    """Page for batch track renaming: singles, tracks of different albums.

    Tracks are read from their tags first. A track is Ready when its title
    and artist match a result on the album of its tags, or on a single
    album (compilations aside). Files are named with the music format of
    the settings.
    """

    default_path_type = "music"
    media_type = MediaType.MUSIC
    content_type = ContentType.TRACK
    factory_type = "track"
    parse = staticmethod(parse_track)
    same_work = staticmethod(same_track)
    localized = False
    describe = staticmethod(describe_track)

    def make_ops(self) -> MusicFileOperations:
        return MusicFileOperations()

    def organize_method(self) -> Callable[..., Dict[str, Any]]:
        return self._ops.organize_items_batch

    def preview_name(self, item: Any, file: Path) -> str:
        folders, name = self._ops.batch_target(item, file, True)
        return "/".join([*folders, name])

    def page_title(self) -> str:
        return tr("music", "Music")

    def empty_hint(self) -> str:
        return tr("tracks_drop_hint", "Drop audio files or folders, or click to browse")

    def add_more_text(self) -> str:
        return tr("add_more_tracks", "+ Add more tracks")

    def query_placeholder(self) -> str:
        return tr("track_title_artist", "Title (optional artist)")
