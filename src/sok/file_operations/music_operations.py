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
File operations for music media.

This module handles:
- Detection and extraction of information from audio file names
- Reading metadata (ID3, FLAC tags, etc.)
- Automatic track renaming
- Organization by artist/album
"""

import os
import re
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
from sok.core.interfaces import FileOperations, MediaItem
from sok.core.utils import format_name
from sok.file_operations.base_operations import FileParsingMixin, FileValidationMixin
from mutagen import File

logger = logging.getLogger(__name__)


class MusicFileOperations(FileOperations, FileParsingMixin, FileValidationMixin):
    """File operations for music files.

    Provides methods to extract metadata from audio filenames,
    read embedded tags (ID3, FLAC), organize by artist/album,
    and rename tracks according to music conventions.
    """

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported audio file extensions.

        Returns:
            List of lowercase extensions including mp3, flac, wav, etc.
        """
        return [
            ".mp3",
            ".flac",
            ".wav",
            ".m4a",
            ".aac",
            ".ogg",
            ".opus",
            ".wma",
            ".ape",
            ".alac",
            ".aiff",
            ".dsd",
            ".dsf",
        ]

    def extract_info_from_filename(self, filename: str) -> Dict[str, Any]:
        """Extract information from an audio filename.

        Supports formats:
        - '01 - Titre.mp3'
        - 'Artiste - Album - 01 - Titre.mp3'
        - '01. Titre.mp3'
        - 'Track 01 Titre.mp3'

        Args:
            filename: File name to parse.

        Returns:
            Dictionary with extracted information.
        """
        info: Dict[str, Any] = {
            "original_filename": filename,
            "extension": os.path.splitext(filename)[1].lower(),
            "artist": None,
            "album": None,
            "track_number": None,
            "disc_number": None,
            "title": None,
            "year": None,
            "genre": None,
            "bitrate": None,
            "sample_rate": None,
        }

        name_without_ext = os.path.splitext(filename)[0]

        pattern_full = r"^(?P<artist>[^-]+)\s*-\s*(?P<album>[^-]+)\s*-\s*(?P<track>\d+)\s*-\s*(?P<title>.+)$"
        match = re.match(pattern_full, name_without_ext)

        if match:
            info["artist"] = match.group("artist").strip()
            info["album"] = match.group("album").strip()
            info["track_number"] = int(match.group("track"))
            info["title"] = match.group("title").strip()
            return info

        pattern_disc = r"^(?:CD|Disc|Disk)?\s*(?P<disc>\d+)[-\s]*(?P<track>\d+)[.\s-]+(?P<title>.+)$"
        match = re.match(pattern_disc, name_without_ext, re.IGNORECASE)

        if match:
            info["disc_number"] = int(match.group("disc"))
            info["track_number"] = int(match.group("track"))
            info["title"] = match.group("title").strip()
            return info

        pattern_track = r"^(?P<track>\d+)[.\s-]+(?P<title>.+)$"
        match = re.match(pattern_track, name_without_ext)

        if match:
            info["track_number"] = int(match.group("track"))
            info["title"] = match.group("title").strip()
            return info

        pattern_word = r"^Track\s+(?P<track>\d+)\s+(?P<title>.+)$"
        match = re.match(pattern_word, name_without_ext, re.IGNORECASE)

        if match:
            info["track_number"] = int(match.group("track"))
            info["title"] = match.group("title").strip()
            return info

        info["title"] = name_without_ext.strip()

        return info

    def read_metadata(self, file_path: str) -> Dict[str, Any]:
        """Read metadata from an audio file.

        Reads ID3, FLAC tags, and other embedded metadata.

        Args:
            file_path: Audio file path.

        Returns:
            Dictionary with read metadata.
        """
        metadata: Dict[str, Any] = {
            "artist": None,
            "album": None,
            "title": None,
            "track_number": None,
            "disc_number": None,
            "year": None,
            "genre": None,
            "album_artist": None,
            "composer": None,
            "duration": None,
            "bitrate": None,
            "sample_rate": None,
        }

        try:
            audio = File(file_path, easy=True)

            if audio is not None:
                tag_mapping = {
                    "artist": ["artist", "TPE1"],
                    "album": ["album", "TALB"],
                    "title": ["title", "TIT2"],
                    "genre": ["genre", "TCON"],
                    "album_artist": ["albumartist", "TPE2"],
                    "composer": ["composer", "TCOM"],
                }

                for key, tags in tag_mapping.items():
                    for tag in tags:
                        if tag in audio:
                            value = audio[tag]
                            metadata[key] = (
                                value[0] if isinstance(value, list) else value
                            )
                            break

                if "tracknumber" in audio or "TRCK" in audio:
                    track = audio.get("tracknumber") or audio.get("TRCK")
                    if track:
                        track_str = track[0] if isinstance(track, list) else track
                        metadata["track_number"] = int(str(track_str).split("/")[0])

                if "discnumber" in audio or "TPOS" in audio:
                    disc = audio.get("discnumber") or audio.get("TPOS")
                    if disc:
                        disc_str = disc[0] if isinstance(disc, list) else disc
                        metadata["disc_number"] = int(str(disc_str).split("/")[0])

                year_tags = ["date", "year", "TDRC", "TYER"]
                for tag in year_tags:
                    if tag in audio:
                        year_value = audio[tag]
                        year_str = (
                            year_value[0]
                            if isinstance(year_value, list)
                            else year_value
                        )
                        year_match = re.search(r"\d{4}", str(year_str))
                        if year_match:
                            metadata["year"] = int(year_match.group())
                            break

                if hasattr(audio.info, "length"):
                    metadata["duration"] = audio.info.length
                if hasattr(audio.info, "bitrate"):
                    metadata["bitrate"] = audio.info.bitrate
                if hasattr(audio.info, "sample_rate"):
                    metadata["sample_rate"] = audio.info.sample_rate

        except ImportError:
            pass
        except (OSError, ValueError) as e:
            logger.exception("Metadata reading error %s", file_path, exc_info=e)

        return metadata

    def generate_new_filename(
        self, media_item: Optional[MediaItem], original_filename: str
    ) -> str:
        """Generate a new filename for an audio track.

        Format: '01 - Track Title.mp3'

        Args:
            media_item: The media item (Album).
            original_filename: Original filename.

        Returns:
            New filename.
        """
        info = self.extract_info_from_filename(original_filename)
        extension = info["extension"]

        if info["track_number"] and info["title"]:
            track_num = str(info["track_number"]).zfill(2)
            return format_name(f"{track_num} - {info['title']}{extension}")
        elif info["title"]:
            return format_name(f"{info['title']}{extension}")

        return original_filename

    def organize_by_artist_album(
        self,
        source_path: str,
        dest_path: str,
        use_metadata: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Organize audio files by Artist/Album.

        Created structure: Artist/Album (Year)/tracks

        Args:
            source_path: Source folder.
            dest_path: Destination folder.
            use_metadata: Use file metadata.
            dry_run: Simulation mode.

        Returns:
            Organization report.
        """
        report: Dict[str, Any] = {
            "moved": [],
            "errors": [],
            "total_files": 0,
            "total_moved": 0,
            "artists": set(),
            "albums": set(),
        }

        for root, dirs, files in os.walk(source_path):
            for file in files:
                if not any(
                    file.lower().endswith(ext) for ext in self.supported_extensions
                ):
                    continue

                report["total_files"] += 1
                source_file = os.path.join(root, file)

                artist = "Unknown Artist"
                album = "Unknown Album"
                year = None

                if use_metadata:
                    metadata = self.read_metadata(source_file)
                    if metadata["artist"]:
                        artist = metadata["artist"]
                    if metadata["album"]:
                        album = metadata["album"]
                    year = metadata.get("year")
                else:
                    path_parts = Path(source_file).parts
                    if len(path_parts) >= 3:
                        album = path_parts[-2]
                    if len(path_parts) >= 4:
                        artist = path_parts[-3]

                artist_folder = format_name(artist)
                if year:
                    album_folder = format_name(f"{album} ({year})")
                else:
                    album_folder = format_name(album)

                dest_folder = os.path.join(dest_path, artist_folder, album_folder)

                new_filename = self.generate_new_filename(None, file)
                dest_file = os.path.join(dest_folder, new_filename)

                # Move the file
                if not dry_run:
                    try:
                        os.makedirs(dest_folder, exist_ok=True)
                        os.rename(source_file, dest_file)
                        report["moved"].append({"from": source_file, "to": dest_file})
                        report["total_moved"] += 1
                        report["artists"].add(artist)
                        report["albums"].add(f"{artist} - {album}")
                    except OSError as e:
                        logger.exception(
                            "Music organize move failed for %s", source_file, exc_info=e
                        )
                        report["errors"].append({"file": source_file, "error": str(e)})
                else:
                    report["moved"].append({"from": source_file, "to": dest_file})
                    report["total_moved"] += 1
                    report["artists"].add(artist)
                    report["albums"].add(f"{artist} - {album}")

        report["artists"] = sorted(list(report["artists"]))
        report["albums"] = sorted(list(report["albums"]))

        return report

    def find_audio_files(self, directory: str, recursive: bool = True) -> List[str]:
        """Find all audio files in a directory.

        Args:
            directory: Directory to scan.
            recursive: Enable recursive search.

        Returns:
            List of audio file paths.
        """
        return self.get_files_by_extension(
            directory, self.supported_extensions, recursive
        )

    def find_files(self, directory: str, recursive: bool = True) -> List[str]:
        """Unified alias for find_audio_files."""
        return self.find_audio_files(directory, recursive)
