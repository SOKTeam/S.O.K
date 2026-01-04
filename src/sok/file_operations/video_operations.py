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
File operations for video media (movies, series, documentaries).

This module handles:
- Detection and extraction of information from file names
- Automatic renaming according to conventions
- Organization and creation of folder structure
- Quality and language detection
"""

from pathlib import Path
from sok.core.utils import format_name
from sok.core.interfaces import MediaItem
from sok.file_operations.base_operations import FileParsingMixin, FileValidationMixin

import os
import shutil
import re
import logging
from typing import Dict, Any, List, Optional, Callable
from sok.config.config_manager import get_config_manager
from sok.media.video.series import Series
from sok.media.video.movie import Movie
import subprocess
import json

logger = logging.getLogger(__name__)


class VideoFileOperations(FileParsingMixin, FileValidationMixin):
    """File operations for video media (movies, series, documentaries).

    Provides methods to extract metadata from video filenames,
    organize files into folder structures, and rename according
    to media conventions.
    """

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported video file extensions.

        Returns:
            List of lowercase extensions including mkv, mp4, avi, etc.
        """
        return [
            ".mkv",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".mpg",
            ".mpeg",
            ".3gp",
            ".ogv",
            ".ts",
            ".m2ts",
        ]

    def extract_info_from_filename(self, filename: str) -> Dict[str, Any]:
        """Extract information from a video filename.

        Supports formats:
        - Series: 'Name S01E01 Title.mkv' or 'Name 1x01 Title.mkv'
        - Movies: 'Title (2020) 1080p.mkv'

        Args:
            filename: File name to parse.

        Returns:
            Dictionary with extracted information.
        """
        info: Dict[str, Any] = {
            "original_filename": filename,
            "extension": os.path.splitext(filename)[1].lower(),
            "type": None,
            "title": None,
            "year": None,
            "season": None,
            "episode": None,
            "quality": None,
            "codec": None,
            "audio": None,
            "language": None,
            "source": None,
            "release_group": None,
        }

        rest = ""
        series_pattern = r"(?P<title>.*?)[.\s-]+S(?P<season>\d{1,2})E(?P<episode>\d{1,2})(?P<rest>.*)"
        match = re.search(series_pattern, filename, re.IGNORECASE)

        if match:
            info["type"] = "series"
            info["title"] = self.clean_title(match.group("title"))
            info["season"] = int(match.group("season"))
            info["episode"] = int(match.group("episode"))
            rest = match.group("rest")
        else:
            alt_pattern = r"(?P<title>.*?)[.\s-]+(?P<season>\d{1,2})x(?P<episode>\d{1,2})(?P<rest>.*)"
            match = re.search(alt_pattern, filename, re.IGNORECASE)

            if match:
                info["type"] = "series"
                info["title"] = self.clean_title(match.group("title"))
                info["season"] = int(match.group("season"))
                info["episode"] = int(match.group("episode"))
                rest = match.group("rest")
            else:
                info["type"] = "movie"

                info["year"] = self.extract_year(filename)
                if info["year"]:
                    info["title"] = self.clean_title(
                        filename.split(str(info["year"]))[0]
                    )
                else:
                    info["title"] = self.clean_title(os.path.splitext(filename)[0])

                rest = filename

        if rest:
            quality_info = self.extract_quality_metadata(rest)
            info.update(quality_info)

        return info

    def _find_existing_season_folder(
        self, series_path: str, season_num: int
    ) -> Optional[str]:
        """Find an existing season folder on disk.

        Supports different formats: Season 1, Season 01, Saison 1, etc.

        Args:
            series_path: Path to the series folder.
            season_num: Season number to find.

        Returns:
            Path to the existing season folder, or None if not found.
        """
        if not os.path.exists(series_path):
            return None

        season_num_padded = str(season_num).zfill(2)
        season_keywords = ["season", "saison", "staffel", "temporada", "s"]

        for item in os.listdir(series_path):
            item_path = os.path.join(series_path, item)
            if not os.path.isdir(item_path):
                continue

            item_lower = item.lower()

            for keyword in season_keywords:
                patterns = [
                    f"{keyword} {season_num}",
                    f"{keyword} {season_num_padded}",
                    f"{keyword}{season_num_padded}",
                    f"{keyword}{season_num}",
                ]

                for pattern in patterns:
                    if (
                        item_lower == pattern
                        or item_lower.startswith(f"{pattern} ")
                        or item_lower.startswith(f"{pattern}-")
                    ):
                        return item_path

                if keyword in item_lower:
                    match = re.search(rf"{keyword}\s*(\d+)", item_lower)
                    if match and int(match.group(1)) == season_num:
                        return item_path

        return None

    def _find_season_in_structure(
        self, folder_structure: List[str], season_num: int
    ) -> str:
        """Find the corresponding season folder name in the structure.

        Args:
            folder_structure: List of folders (series + seasons).
            season_num: Season number to find.

        Returns:
            Season folder name (e.g., 'Season 1 - Pilot Season').
        """
        season_keywords = ["season", "saison", "staffel", "temporada"]

        for folder in folder_structure[1:]:
            folder_lower = folder.lower()

            for keyword in season_keywords:
                match = re.match(rf"^{keyword}\s*(\d+)", folder_lower)
                if match and int(match.group(1)) == season_num:
                    return folder

        config = get_config_manager()
        translations = (
            config.load_language() if hasattr(config, "load_language") else {}
        )
        season_word = translations.get("season", "Season")
        return f"{season_word} {season_num}"

    def generate_new_filename(
        self, media_item: MediaItem, original_filename: str
    ) -> str:
        """Generate a new filename for a video.

        Uses the custom format defined in settings.

        Default series format: '{title} S{season}E{episode} {episode_title}'
        Default movie format: '{title} ({year})'

        Args:
            media_item: The media item.
            original_filename: Original filename.

        Returns:
            New filename.
        """

        config = get_config_manager()
        info = self.extract_info_from_filename(original_filename)
        extension = info["extension"]

        if isinstance(media_item, Series):
            series_item = media_item
            if info["season"] is not None and info["episode"] is not None:
                season_num = info["season"]
                episode_num = info["episode"]
                season_str = str(season_num).zfill(2)
                episode_str = str(episode_num).zfill(2)
                episode_code = f"S{season_str}E{episode_str}"

                episode_title = series_item.get_episode_info(episode_code) or ""

                video_format = config.get(
                    "video_format", "{title} S{season}E{episode} {episode_title}"
                )

                try:
                    new_name = video_format.format(
                        title=series_item.title,
                        season=season_str,
                        episode=episode_str,
                        episode_title=episode_title,
                        season_num=season_num,
                        episode_num=episode_num,
                    )
                except ValueError:
                    new_name = video_format.format(
                        title=series_item.title,
                        season=int(season_num),
                        episode=int(episode_num),
                        episode_title=episode_title,
                        season_num=season_num,
                        episode_num=episode_num,
                    )

                new_name = re.sub(r"\s+", " ", new_name).strip()

                return format_name(f"{new_name}{extension}")

        elif isinstance(media_item, Movie):
            movie_item = media_item
            movie_format = config.get("movie_format", "{title} ({year})")

            new_name = movie_format.format(
                title=movie_item.title,
                year=movie_item.year or "",
                quality=info.get("quality", "") or "",
            )

            new_name = re.sub(r"\s*\(\s*\)\s*", "", new_name)
            new_name = re.sub(r"\s+", " ", new_name).strip()

            return format_name(f"{new_name}{extension}")

        return original_filename

    def organize_files(
        self,
        source_path: str,
        dest_path: str,
        media_item: MediaItem,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, Any]:
        """Organize video files into a folder structure.

        For series: Series Name/Season 01/files
        For movies: Movie Name (2020)/file

        Args:
            source_path: Source folder.
            dest_path: Destination folder.
            media_item: The media item.
            dry_run: If True, simulate without making changes.
            progress_callback: Function called with (current, total, filename)
                to report progress.

        Returns:
            Organization report (moved files, errors, etc.).
        """

        report: Dict[str, Any] = {
            "moved": [],
            "errors": [],
            "total_files": 0,
            "total_moved": 0,
        }

        all_video_files = []
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if any(file.endswith(ext) for ext in self.supported_extensions):
                    all_video_files.append((root, file))

        total_files = len(all_video_files)
        report["total_files"] = total_files

        folder_structure = media_item.get_folder_structure()

        if isinstance(media_item, Series):
            series_folder = os.path.join(dest_path, folder_structure[0])
            if not dry_run and not os.path.exists(series_folder):
                os.makedirs(series_folder, exist_ok=True)
            base_path = series_folder
        else:
            base_path = os.path.join(dest_path, folder_structure[0])
            if not dry_run and not os.path.exists(base_path):
                os.makedirs(base_path, exist_ok=True)

        for idx, (root, file) in enumerate(all_video_files):
            source_file = os.path.join(root, file)

            if progress_callback:
                progress_callback(idx + 1, total_files, file)

                info = self.extract_info_from_filename(file)

                if isinstance(media_item, Series) and info["season"] is not None:
                    season_num = info["season"]

                    existing_season_folder = self._find_existing_season_folder(
                        base_path, season_num
                    )

                    if existing_season_folder:
                        dest_folder = existing_season_folder
                    else:
                        season_folder_name = self._find_season_in_structure(
                            folder_structure, season_num
                        )
                        dest_folder = os.path.join(base_path, season_folder_name)
                else:
                    dest_folder = base_path

                new_filename = self.generate_new_filename(media_item, file)
                dest_file = os.path.join(dest_folder, new_filename)

                if not dry_run:
                    try:
                        if not os.path.exists(dest_folder):
                            os.makedirs(dest_folder, exist_ok=True)

                        os.rename(source_file, dest_file)
                        report["moved"].append({"from": source_file, "to": dest_file})
                        report["total_moved"] += 1
                    except OSError as e:
                        logger.exception(
                            "Video organize move failed for %s", source_file, exc_info=e
                        )
                        report["errors"].append({"file": source_file, "error": str(e)})
                else:
                    report["moved"].append({"from": source_file, "to": dest_file})
                    report["total_moved"] += 1

        return report

    def organize_files_list(
        self,
        files: List[Path],
        dest_path: str,
        media_item: MediaItem,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, Any]:
        """Organize a list of video files into a folder structure.

        Unlike organize_files which scans a folder, this method
        directly processes a list of files (which can come from multiple folders).

        Args:
            files: List of files to organize.
            dest_path: Destination folder.
            media_item: The media item.
            dry_run: If True, simulate without making changes.
            progress_callback: Function called with (current, total, filename).

        Returns:
            Organization report.
        """

        config = get_config_manager()
        create_folders = config.get("create_folders", True)
        skip_duplicates = config.get("skip_duplicates", False)
        backup_before_rename = config.get("backup_before_rename", False)
        log_operations = config.get("log_operations", True)

        report: Dict[str, Any] = {
            "moved": [],
            "errors": [],
            "skipped": [],
            "total_files": len(files),
            "total_moved": 0,
        }

        folder_structure = media_item.get_folder_structure()

        if isinstance(media_item, Series):
            series_folder = os.path.join(dest_path, folder_structure[0])
            if not dry_run and not os.path.exists(series_folder):
                if create_folders:
                    os.makedirs(series_folder, exist_ok=True)
                else:
                    report["errors"].append(
                        {
                            "file": series_folder,
                            "error": "Missing folder and creation disabled",
                        }
                    )
                    return report
            base_path = series_folder
        else:
            base_path = os.path.join(dest_path, folder_structure[0])
            if not dry_run and not os.path.exists(base_path):
                if create_folders:
                    os.makedirs(base_path, exist_ok=True)
                else:
                    report["errors"].append(
                        {
                            "file": base_path,
                            "error": "Missing folder and creation disabled",
                        }
                    )
                    return report

        for idx, file_path in enumerate(files):
            file = file_path.name
            source_file = str(file_path)

            if progress_callback:
                progress_callback(idx + 1, len(files), file)

            info = self.extract_info_from_filename(file)

            if isinstance(media_item, Series) and info["season"] is not None:
                season_num = info["season"]

                existing_season_folder = self._find_existing_season_folder(
                    base_path, season_num
                )

                if existing_season_folder:
                    dest_folder = existing_season_folder
                else:
                    season_folder_name = self._find_season_in_structure(
                        folder_structure, season_num
                    )
                    dest_folder = os.path.join(base_path, season_folder_name)
            else:
                dest_folder = base_path

            new_filename = self.generate_new_filename(media_item, file)
            dest_file = os.path.join(dest_folder, new_filename)

            if skip_duplicates and os.path.exists(dest_file):
                report["skipped"].append(
                    {"file": source_file, "reason": "File already exists"}
                )
                if log_operations:
                    logger.info("Skipped duplicate: %s", source_file)
                continue

            if not dry_run:
                try:
                    if not os.path.exists(dest_folder):
                        if create_folders:
                            os.makedirs(dest_folder, exist_ok=True)
                        else:
                            report["errors"].append(
                                {
                                    "file": source_file,
                                    "error": f"Folder {dest_folder} missing and creation disabled",
                                }
                            )
                            continue

                    if backup_before_rename and os.path.exists(dest_file):
                        backup_path = f"{dest_file}.backup"
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                        shutil.copy2(dest_file, backup_path)
                        if log_operations:
                            logger.info("Backup created: %s", backup_path)
                    os.rename(source_file, dest_file)
                    report["moved"].append({"from": source_file, "to": dest_file})
                    report["total_moved"] += 1
                    if log_operations:
                        logger.info("Moved: %s -> %s", source_file, dest_file)
                except OSError as e:
                    logger.exception(
                        "Video organize list move failed for %s",
                        source_file,
                        exc_info=e,
                    )
                    report["errors"].append({"file": source_file, "error": str(e)})
            else:
                report["moved"].append({"from": source_file, "to": dest_file})
                report["total_moved"] += 1

        return report

    def detect_video_info(self, file_path: str) -> Dict[str, Any]:
        """Detect video information (resolution, codec, duration, etc.).

        Note:
            Requires ffprobe or mediainfo installed.

        Args:
            file_path: Video file path.

        Returns:
            Detailed video information.
        """

        info: Dict[str, Any] = {
            "resolution": None,
            "codec": None,
            "duration": None,
            "bitrate": None,
            "audio_tracks": [],
            "subtitle_tracks": [],
        }

        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                file_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)

            # Extract video info
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    info["resolution"] = f"{stream.get('width')}x{stream.get('height')}"
                    info["codec"] = stream.get("codec_name")

                elif stream.get("codec_type") == "audio":
                    info["audio_tracks"].append(
                        {
                            "codec": stream.get("codec_name"),
                            "language": stream.get("tags", {}).get(
                                "language", "unknown"
                            ),
                            "channels": stream.get("channels"),
                        }
                    )

                elif stream.get("codec_type") == "subtitle":
                    info["subtitle_tracks"].append(
                        {"language": stream.get("tags", {}).get("language", "unknown")}
                    )

            format_info = data.get("format", {})
            info["duration"] = float(format_info.get("duration", 0))
            info["bitrate"] = int(format_info.get("bit_rate", 0))

        except (FileNotFoundError, subprocess.SubprocessError):
            pass

        return info

    def find_video_files(self, directory: str, recursive: bool = True) -> List[str]:
        """Find all video files in a directory.

        Args:
            directory: Directory to scan.
            recursive: Enable recursive search in subfolders.

        Returns:
            List of video file paths.
        """
        return self.get_files_by_extension(
            directory, self.supported_extensions, recursive
        )

    def find_files(self, directory: str, recursive: bool = True) -> List[str]:
        """Unified alias for find_video_files."""
        return self.find_video_files(directory, recursive)
