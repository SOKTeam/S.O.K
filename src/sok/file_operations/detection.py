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
Detection of the media type of files dropped in the app.

The user drops files or folders without saying what they are. This module
sorts them into groups that one page of the app can handle at a time. The
batch pages take all their files at once: one group of movies, one of
tracks, one of books, one of games. The other pages take one item at a
time: one group per series and per album. Files whose type is a guess are
kept apart for the user to check.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from sok.core.interfaces import ContentType
from sok.core.utils import natural_key
from sok.file_operations.book_operations import BookFileOperations
from sok.file_operations.game_operations import GameFileOperations
from sok.file_operations.music_operations import MusicFileOperations
from sok.file_operations.video_operations import VideoFileOperations

# Accepted by the book and game pages, but too common elsewhere to mean a
# book or a game: a readme, an installer, the archive of a movie. Only the
# page the user picks accepts them.
GENERIC_EXTENSIONS = {".txt", ".rtf", ".doc", ".docx", ".exe", ".zip", ".rar", ".7z"}
# Disc images can hold a game as well as a DVD or a Blu-ray.
AMBIGUOUS_EXTENSIONS = {".iso", ".img"}

# Numbers that only an episode has. The video parser also accepts weaker
# forms ("Episode 4", "1.05") that some movie names contain.
EPISODE_PATTERN = re.compile(
    r"(?<![a-z])S\d{1,2}\]?[.\s_\-]?\[?E\d{1,3}"
    r"|(?:^|[.\s_\-])\d{1,2}x\d{1,3}(?:$|[.\s_\-])"
    r"|(?:season|saison)[.\s_\-]?\d{1,2}[.\s_\-]+(?:episode|ep|e)[.\s_\-]?\d{1,3}",
    re.IGNORECASE,
)
# "Season 1", "Saison 01", "Staffel 2", "S01", "Show S01"…
SEASON_FOLDER_PATTERN = re.compile(
    r"(?:^|[\s._\-])(?:s|season|saison|staffel|temporada|stagione|sezon)"
    r"[\s._\-]?\d{1,2}$",
    re.IGNORECASE,
)
# "CD1", "Disc 2", "Disque 1"…: the album is the folder above.
DISC_FOLDER_PATTERN = re.compile(
    r"^(?:cd|disc|disk|disque)[\s._\-]?\d{1,2}$", re.IGNORECASE
)
SAMPLE_PATTERN = re.compile(r"(?:^|[\s._\-\[(])sample(?:$|[\s._\-\])])", re.IGNORECASE)

# Order of the groups in a report.
KIND_ORDER = [
    ContentType.MOVIE,
    ContentType.EPISODE,
    ContentType.ALBUM,
    ContentType.TRACK,
    ContentType.BOOK,
    ContentType.GAME,
]
# Kinds whose page renames many items at once: one group for all files.
BATCH_KINDS = {ContentType.MOVIE, ContentType.TRACK, ContentType.BOOK, ContentType.GAME}
# Audio files of a folder with fewer files are tracks, not an album.
ALBUM_MIN_TRACKS = 3


@dataclass
class DetectedFile:
    """One file and the type found for it.

    Attributes:
        path: The file.
        kind: MOVIE, EPISODE, ALBUM (a track of an album), TRACK (a track on
            its own), BOOK or GAME.
        title: Series or album title, book or game title, or None.
        certain: False when the type is a guess the user should check.
        reason: Why the type was chosen, for the log and the interface.
    """

    path: Path
    kind: ContentType
    title: Optional[str]
    certain: bool
    reason: str


@dataclass
class MediaGroup:
    """Files that one page of the app organizes together.

    Attributes:
        kind: MOVIE, EPISODE, ALBUM, TRACK, BOOK or GAME.
        title: Series or album title; None for the kinds of BATCH_KINDS,
            whose files are all in one group.
        files: The files, sorted naturally.
    """

    kind: ContentType
    title: Optional[str]
    files: List[Path] = field(default_factory=list)
    key: str = field(default="", repr=False)


@dataclass
class DetectionReport:
    """Result of detect_sources().

    Attributes:
        groups: Sure files, movies first, then series, albums, books, games.
        to_check: Files whose type is a guess, with the suggested type.
        ignored: Files that are not media, hidden files and samples.
    """

    groups: List[MediaGroup] = field(default_factory=list)
    to_check: List[DetectedFile] = field(default_factory=list)
    ignored: List[Path] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        """Number of media files found, checked or not."""
        return sum(len(g.files) for g in self.groups) + len(self.to_check)

    def add(self, item: DetectedFile) -> MediaGroup:
        """Put a file in the group of its series, album, book or game.

        The group is created if needed, and the groups stay in page order.

        Args:
            item: The file, whose type is taken as sure.

        Returns:
            The group the file went into.
        """
        key = _group_key(item)
        group = next(
            (g for g in self.groups if g.kind == item.kind and g.key == key), None
        )
        if group is None:
            title = None if item.kind in BATCH_KINDS else item.title
            group = MediaGroup(item.kind, title, key=key)
            self.groups.append(group)
            self.groups.sort(
                key=lambda g: (
                    KIND_ORDER.index(g.kind),
                    natural_key(Path(g.title or "")),
                )
            )
        if item.path not in group.files:
            group.files.append(item.path)
            group.files.sort(key=natural_key)
        return group


class MediaTypeDetector:
    """Find the type of media files from their name, extension and folder."""

    def __init__(self) -> None:
        self._video = VideoFileOperations()
        self._music = MusicFileOperations()
        self._book = BookFileOperations()
        self._game = GameFileOperations()
        self._extensions: Dict[str, ContentType] = {}
        for ops, kind in (
            (self._video, ContentType.MOVIE),
            (self._music, ContentType.ALBUM),
            (self._book, ContentType.BOOK),
            (self._game, ContentType.GAME),
        ):
            for ext in ops.supported_extensions:
                if ext.lower() not in GENERIC_EXTENSIONS:
                    self._extensions.setdefault(ext.lower(), kind)

    @property
    def supported_extensions(self) -> List[str]:
        """Extensions of the files the app can organize, sorted."""
        return sorted(self._extensions)

    def is_ignored(self, path: Path) -> bool:
        """Return True for files that are not media or must be skipped.

        Hidden files (including the "._" files macOS writes on other disks),
        video samples and generic files (GENERIC_EXTENSIONS) are skipped.
        """
        if path.name.startswith("."):
            return True
        kind = self._extensions.get(path.suffix.lower())
        if kind is None:
            return True
        return kind == ContentType.MOVIE and bool(SAMPLE_PATTERN.search(path.stem))

    def detect_file(self, path: Path) -> Optional[DetectedFile]:
        """Find the type of one file, without looking at the files around it.

        Args:
            path: The file.

        Returns:
            The detected file, or None if it is ignored (see is_ignored).
        """
        if self.is_ignored(path):
            return None
        kind = self._extensions[path.suffix.lower()]

        if kind == ContentType.MOVIE:
            info = self._video.extract_info_from_filename(path.name)
            if info["type"] == "series":
                title = info["title"] or _series_folder_title(path)
                if EPISODE_PATTERN.search(path.stem):
                    return DetectedFile(
                        path, ContentType.EPISODE, title, True, "episode number"
                    )
                return DetectedFile(
                    path,
                    ContentType.EPISODE,
                    title,
                    False,
                    "episode number without season",
                )
            if EPISODE_PATTERN.search(path.stem):
                return DetectedFile(
                    path,
                    ContentType.EPISODE,
                    _series_folder_title(path),
                    True,
                    "episode number",
                )
            if SEASON_FOLDER_PATTERN.search(path.parent.name):
                return DetectedFile(
                    path,
                    ContentType.EPISODE,
                    _series_folder_title(path),
                    False,
                    "season folder without episode number",
                )
            return DetectedFile(path, ContentType.MOVIE, None, True, "video")

        if kind == ContentType.ALBUM:
            return DetectedFile(path, kind, _album_folder(path).name, True, "audio")

        if kind == ContentType.BOOK:
            info = self._book.extract_info_from_filename(path.name)
            return DetectedFile(path, kind, info["title"] or path.stem, True, "book")

        info = self._game.extract_info_from_filename(path.name)
        title = info["title"] or path.stem
        if path.suffix.lower() in AMBIGUOUS_EXTENSIONS:
            return DetectedFile(path, kind, title, False, "disc image")
        return DetectedFile(path, kind, title, True, "game")

    def detect_sources(self, paths: Iterable[Path]) -> DetectionReport:
        """Sort dropped files and folders into groups.

        Folders are scanned recursively. A movie found in a folder that holds
        mostly episodes is kept apart: it is often a bonus of the series.
        Audio files are an album when their folder holds one album (see
        _is_album), tracks on their own otherwise.

        Args:
            paths: Files and folders, in the order they were dropped.

        Returns:
            The groups, the files to check and the ignored files.
        """
        report = DetectionReport()
        detected: List[DetectedFile] = []
        seen = set()
        for file in _walk(paths):
            if file in seen:
                continue
            seen.add(file)
            item = self.detect_file(file)
            if item is None:
                report.ignored.append(file)
            else:
                detected.append(item)

        videos: Dict[Path, List[int]] = {}
        for d in detected:
            if d.kind in (ContentType.MOVIE, ContentType.EPISODE):
                counts = videos.setdefault(d.path.parent, [0, 0])
                counts[d.kind == ContentType.EPISODE] += 1
        for d in detected:
            movies, episodes = videos.get(d.path.parent, [0, 0])
            if d.kind == ContentType.MOVIE and episodes > movies:
                d.kind = ContentType.EPISODE
                d.title = _series_folder_title(d.path)
                d.certain = False
                d.reason = "video next to episodes"

        folders: Dict[Path, List[DetectedFile]] = {}
        for d in detected:
            if d.kind == ContentType.ALBUM:
                folders.setdefault(_album_folder(d.path), []).append(d)
        for files in folders.values():
            if not self._is_album(files):
                for d in files:
                    d.kind = ContentType.TRACK
                    d.title = None

        for d in detected:
            if d.certain:
                report.add(d)
            else:
                report.to_check.append(d)
        report.to_check.sort(key=lambda d: natural_key(d.path))
        return report

    def _is_album(self, files: List[DetectedFile]) -> bool:
        """True if the audio files of a folder are one album.

        An album has at least ALBUM_MIN_TRACKS tracks with the same album in
        their tags, or, without album tags, the same artist. A folder of
        singles by several artists is tracks.
        """
        if len(files) < ALBUM_MIN_TRACKS:
            return False
        albums, artists = set(), set()
        for d in files:
            tags = self._music.read_metadata(str(d.path))
            if tags.get("album"):
                albums.add(tags["album"].casefold())
            artist = tags.get("artist")
            if not artist and " - " in d.path.stem:
                # "Artist - Title.mp3", the usual name of a single.
                artist = d.path.stem.split(" - ", 1)[0]
                if artist.strip().isdigit():
                    # "01 - Title.mp3": a track number, not an artist.
                    artist = None
            if artist:
                artists.add(artist.strip().casefold())
        if albums:
            return len(albums) == 1
        return len(artists) <= 1

    def confirm(
        self, report: DetectionReport, item: DetectedFile, kind: ContentType
    ) -> MediaGroup:
        """Move a file to check into a group, with the type the user chose.

        Args:
            report: The report that holds the file in to_check.
            item: The file to check.
            kind: MOVIE, EPISODE, ALBUM, TRACK, BOOK or GAME.

        Returns:
            The group the file went into.
        """
        if item in report.to_check:
            report.to_check.remove(item)
        title = self._title_for(item, kind)
        return report.add(
            DetectedFile(item.path, kind, title, True, "chosen by the user")
        )

    def _title_for(self, item: DetectedFile, kind: ContentType) -> Optional[str]:
        """Title of a file once its type is known."""
        if kind == item.kind:
            return item.title
        if kind in (ContentType.MOVIE, ContentType.TRACK):
            return None
        if kind == ContentType.EPISODE:
            return _series_folder_title(item.path)
        if kind == ContentType.ALBUM:
            return _album_folder(item.path).name
        ops = self._book if kind == ContentType.BOOK else self._game
        return ops.extract_info_from_filename(item.path.name)["title"] or item.path.stem


def detect_sources(paths: Iterable[Path]) -> DetectionReport:
    """Sort dropped files and folders into groups (see MediaTypeDetector)."""
    return MediaTypeDetector().detect_sources(paths)


def _walk(paths: Iterable[Path]) -> Iterable[Path]:
    """Yield the files of the given paths, folders scanned recursively."""
    for path in paths:
        if path.is_file():
            yield path
        elif path.is_dir():
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for name in files:
                    yield Path(root) / name


def _series_folder_title(path: Path) -> Optional[str]:
    """Series title from the folders: the parent, or above a season folder."""
    folder = path.parent
    if SEASON_FOLDER_PATTERN.search(folder.name):
        title = SEASON_FOLDER_PATTERN.sub("", folder.name).strip(" ._-")
        if title:
            return title
        folder = folder.parent
    return folder.name or None


def _album_folder(path: Path) -> Path:
    """Folder of the album: the parent, or above a "CD1" or "Disc 2" folder."""
    folder = path.parent
    if DISC_FOLDER_PATTERN.match(folder.name):
        return folder.parent
    return folder


def _group_key(item: DetectedFile) -> str:
    """Key that puts the files of one group together: same series, same album."""
    if item.kind in BATCH_KINDS:
        return ""
    if item.kind == ContentType.ALBUM:
        return str(_album_folder(item.path))
    return re.sub(r"[^0-9a-z]+", "", (item.title or "").casefold())
