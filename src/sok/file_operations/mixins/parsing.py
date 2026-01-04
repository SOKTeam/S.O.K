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
Parsing mixin for file operations.

Provides utilities to extract information from filenames:
- Year extraction
- Quality metadata extraction (codec, resolution, source...)
- Title and filename cleaning
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional


VIDEO_QUALITY_PATTERNS: Dict[str, str] = {
    "2160p": "4K",
    "1080p": "1080p",
    "720p": "720p",
    "480p": "480p",
    "4K": "4K",
    "UHD": "4K",
    "HD": "HD",
}

VIDEO_CODECS: List[str] = [
    "x264",
    "x265",
    "H264",
    "H265",
    "HEVC",
    "XviD",
    "DivX",
    "VP9",
    "AV1",
]

AUDIO_CODECS: List[str] = [
    "AAC",
    "AC3",
    "DTS",
    "TrueHD",
    "Atmos",
    "DD5.1",
    "DD+",
    "EAC3",
    "FLAC",
    "MP3",
]

CONTENT_SOURCES: List[str] = [
    "BluRay",
    "BRRip",
    "WEB-DL",
    "WEBRip",
    "HDTV",
    "DVDRip",
    "DVD",
    "REMUX",
]

LANGUAGE_PATTERNS: Dict[str, str] = {
    "FRENCH": "fr",
    "VOSTFR": "fr-sub",
    "MULTI": "multi",
    "TRUEFRENCH": "fr",
    "VFF": "fr",
    "VFQ": "fr-qc",
    "ENGLISH": "en",
    "GERMAN": "de",
    "SPANISH": "es",
}

INVALID_FILENAME_CHARS: str = '<>:"/\\|?*'


class FileParsingMixin:
    """
    Mixin providing filename parsing utilities.

    Used by all specific operations classes to avoid
    parsing code duplication.
    """

    @staticmethod
    def extract_year(text: str) -> Optional[int]:
        """Extract a year from text.

        Args:
            text: Text potentially containing a year.

        Returns:
            Extracted year or None.
        """
        year_pattern = r"\((\d{4})\)|\b(19\d{2}|20\d{2})\b"
        match = re.search(year_pattern, text)
        if match:
            year_str = match.group(1) or match.group(2)
            year = int(year_str)
            if 1900 <= year <= 2100:
                return year
        return None

    @staticmethod
    def extract_quality_metadata(text: str) -> Dict[str, Optional[str]]:
        """Extract quality metadata from text (filename).

        Args:
            text: Text to analyze.

        Returns:
            Extracted metadata (quality, codec, audio, source, language).
        """
        info: Dict[str, Optional[str]] = {
            "quality": None,
            "codec": None,
            "audio": None,
            "source": None,
            "language": None,
            "release_group": None,
        }

        text_lower = text.lower()

        for pattern, quality in VIDEO_QUALITY_PATTERNS.items():
            if pattern.lower() in text_lower:
                info["quality"] = quality
                break

        for codec in VIDEO_CODECS:
            if codec.lower() in text_lower:
                info["codec"] = codec.upper()
                break

        for audio in AUDIO_CODECS:
            if audio.lower() in text_lower:
                info["audio"] = audio.upper()
                break

        for source in CONTENT_SOURCES:
            if source.lower() in text_lower:
                info["source"] = source
                break

        for pattern, lang in LANGUAGE_PATTERNS.items():
            if pattern.lower() in text_lower:
                info["language"] = lang
                break

        release_pattern = r"[-\[]([A-Za-z0-9]+)\]?$"
        match = re.search(release_pattern, os.path.splitext(text)[0])
        if match:
            info["release_group"] = match.group(1)

        return info

    @staticmethod
    def clean_title(
        title: str, replace_dots: bool = True, replace_underscores: bool = True
    ) -> str:
        """Clean a title by removing common formatting characters.

        Args:
            title: Title to clean.
            replace_dots: Replace dots with spaces.
            replace_underscores: Replace underscores with spaces.

        Returns:
            Cleaned title.
        """
        if replace_dots:
            title = title.replace(".", " ")
        if replace_underscores:
            title = title.replace("_", " ")

        title = re.sub(r"\s+", " ", title)

        return title.strip()

    @staticmethod
    def clean_filename(filename: str, replace_char: str = "_") -> str:
        """Clean a filename by removing invalid characters.

        Args:
            filename: Filename to clean.
            replace_char: Replacement character.

        Returns:
            Cleaned filename.
        """
        cleaned = filename
        for char in INVALID_FILENAME_CHARS:
            cleaned = cleaned.replace(char, replace_char)

        cleaned = cleaned.strip()
        name, ext = os.path.splitext(cleaned)
        name = name.rstrip(".")
        cleaned = name + ext

        return cleaned

    @staticmethod
    def extract_number_from_text(text: str, pattern: str = r"\d+") -> Optional[int]:
        """Extract the first number from text.

        Args:
            text: Text to analyze.
            pattern: Regex pattern to find the number.

        Returns:
            Found number or None.
        """
        match = re.search(pattern, text)
        if match:
            try:
                return int(match.group())
            except ValueError:
                pass
        return None

    @staticmethod
    def parse_track_disc_number(value: str) -> int:
        """Parse a track/disc number that may be in '1/12' format.

        Args:
            value: Value to parse (e.g., '5' or '5/12').

        Returns:
            Extracted number.
        """
        return int(str(value).split("/")[0])

    @staticmethod
    def normalize_path_for_comparison(path: str) -> str:
        """Normalize a path for comparison (lowercase, unified separators).

        Args:
            path: Path to normalize.

        Returns:
            Normalized path.
        """
        return str(Path(path)).lower().replace("\\", "/")
