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
File operations for video games.

This module handles:
- Detection and extraction of information from game file names
- Automatic renaming
- Organization by platform/console
- Version detection (region, revision, etc.)
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from sok.core.interfaces import FileOperations, MediaItem
from sok.core.utils import format_name
from sok.file_operations.base_operations import FileParsingMixin, FileValidationMixin

logger = logging.getLogger(__name__)


class GameFileOperations(FileOperations, FileParsingMixin, FileValidationMixin):
    """File operations for video game files.

    Provides methods to extract metadata from game filenames,
    detect versions (region, revision), organize by platform,
    and rename according to ROM/ISO conventions.
    """

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported game file extensions.

        Returns:
            List of lowercase extensions including iso, rom, wbfs, etc.
        """
        return [
            ".iso",
            ".bin",
            ".cue",
            ".img",
            ".mds",
            ".mdf",
            ".nrg",
            ".nes",
            ".sfc",
            ".smc",
            ".n64",
            ".z64",
            ".v64",
            ".nds",
            ".3ds",
            ".cia",
            ".gba",
            ".gbc",
            ".gb",
            ".wbfs",
            ".wad",
            ".rvz",
            ".gen",
            ".smd",
            ".32x",
            ".gg",
            ".sms",
            ".cdi",
            ".ps1",
            ".ps2",
            ".ps3",
            ".psp",
            ".psv",
            ".minipsf",
            ".xbe",
            ".xex",
            ".xiso",
            ".exe",
            ".zip",
            ".rar",
            ".7z",
            ".rom",
            ".gcm",
            ".gcz",
            ".rvz",
            ".chd",
        ]

    # Plateformes reconnues
    PLATFORMS = {
        "nes": "Nintendo Entertainment System",
        "snes": "Super Nintendo",
        "n64": "Nintendo 64",
        "gc": "GameCube",
        "wii": "Wii",
        "wiiu": "Wii U",
        "switch": "Nintendo Switch",
        "gb": "Game Boy",
        "gbc": "Game Boy Color",
        "gba": "Game Boy Advance",
        "nds": "Nintendo DS",
        "3ds": "Nintendo 3DS",
        "genesis": "Sega Genesis",
        "megadrive": "Sega Mega Drive",
        "scd": "Sega CD",
        "32x": "Sega 32X",
        "saturn": "Sega Saturn",
        "dreamcast": "Sega Dreamcast",
        "ps1": "PlayStation",
        "psx": "PlayStation",
        "ps2": "PlayStation 2",
        "ps3": "PlayStation 3",
        "ps4": "PlayStation 4",
        "ps5": "PlayStation 5",
        "psp": "PlayStation Portable",
        "vita": "PlayStation Vita",
        "xbox": "Xbox",
        "xbox360": "Xbox 360",
        "xboxone": "Xbox One",
        "xboxsx": "Xbox Series X/S",
        "arcade": "Arcade",
        "mame": "MAME",
        "pc": "PC",
        "dos": "DOS",
    }

    # Region codes
    REGIONS = {
        "usa": "USA",
        "us": "USA",
        "europe": "Europe",
        "eu": "Europe",
        "japan": "Japan",
        "jp": "Japan",
        "jap": "Japan",
        "world": "World",
        "france": "France",
        "fr": "France",
        "germany": "Germany",
        "de": "Germany",
        "spain": "Spain",
        "es": "Spain",
        "italy": "Italy",
        "it": "Italy",
        "uk": "United Kingdom",
        "korea": "Korea",
        "kr": "Korea",
        "china": "China",
        "cn": "China",
        "brazil": "Brazil",
        "br": "Brazil",
    }

    def extract_info_from_filename(self, filename: str) -> Dict[str, Any]:
        """Extract information from a game filename.

        Supports typical ROM formats:
        - 'Game Title (USA).iso'
        - 'Game Title (Europe) (Rev 1).bin'
        - 'Game Title [SLUS-12345].iso'
        - '[Platform] Game Title (Region).rom'

        Args:
            filename: File name to parse.

        Returns:
            Dictionary with extracted information.
        """
        info: Dict[str, Any] = {
            "original_filename": filename,
            "extension": os.path.splitext(filename)[1].lower(),
            "title": None,
            "platform": None,
            "region": None,
            "regions": [],
            "revision": None,
            "version": None,
            "release_code": None,
            "languages": [],
            "tags": [],
            "is_hack": False,
            "is_beta": False,
            "is_demo": False,
            "is_proto": False,
        }

        name_without_ext = os.path.splitext(filename)[0]

        platform_match = re.match(r"^\[([^\]]+)\]\s*(.+)$", name_without_ext)
        if platform_match:
            platform = platform_match.group(1).lower().strip()
            if platform in self.PLATFORMS:
                info["platform"] = self.PLATFORMS[platform]
            name_without_ext = platform_match.group(2)

        parentheses_parts = re.findall(r"\(([^)]+)\)", name_without_ext)
        brackets_parts = re.findall(r"\[([^\]]+)\]", name_without_ext)

        for part in parentheses_parts:
            part_lower = part.lower()

            for region_code, region_name in self.REGIONS.items():
                if region_code in part_lower:
                    info["regions"].append(region_name)
                    if not info["region"]:
                        info["region"] = region_name
                    break

            if "rev" in part_lower or "revision" in part_lower:
                rev_match = re.search(r"rev(?:ision)?\s*(\d+)", part_lower)
                if rev_match:
                    info["revision"] = int(rev_match.group(1))

            if "v" in part_lower or "ver" in part_lower:
                ver_match = re.search(r"v(?:er(?:sion)?)?\s*([\d.]+)", part_lower)
                if ver_match:
                    info["version"] = ver_match.group(1)

            languages = ["en", "fr", "de", "es", "it", "pt", "ja", "zh", "ko"]
            for lang in languages:
                if lang in part_lower:
                    info["languages"].append(lang.upper())

            if "beta" in part_lower:
                info["is_beta"] = True
                info["tags"].append("Beta")
            if "demo" in part_lower:
                info["is_demo"] = True
                info["tags"].append("Demo")
            if "proto" in part_lower or "prototype" in part_lower:
                info["is_proto"] = True
                info["tags"].append("Prototype")
            if "hack" in part_lower:
                info["is_hack"] = True
                info["tags"].append("Hack")
            if "sample" in part_lower:
                info["tags"].append("Sample")
            if "promo" in part_lower or "promotional" in part_lower:
                info["tags"].append("Promo")

        for part in brackets_parts:
            if re.match(r"[A-Z]{4}[_-]?\d{5}", part):
                info["release_code"] = part
            elif part.startswith("!"):
                info["release_code"] = part

        title = re.sub(r"\([^)]+\)", "", name_without_ext)
        title = re.sub(r"\[[^\]]+\]", "", title)
        title = title.strip()

        title = re.sub(r"\s+", " ", title)

        info["title"] = title

        return info

    def detect_platform_from_extension(self, extension: str) -> Optional[str]:
        """Detects the platform from the file extension"""
        ext_to_platform = {
            ".nes": "Nintendo Entertainment System",
            ".sfc": "Super Nintendo",
            ".smc": "Super Nintendo",
            ".n64": "Nintendo 64",
            ".z64": "Nintendo 64",
            ".v64": "Nintendo 64",
            ".nds": "Nintendo DS",
            ".3ds": "Nintendo 3DS",
            ".gba": "Game Boy Advance",
            ".gbc": "Game Boy Color",
            ".gb": "Game Boy",
            ".gen": "Sega Genesis",
            ".smd": "Sega Genesis",
            ".32x": "Sega 32X",
            ".gg": "Game Gear",
            ".psp": "PlayStation Portable",
        }

        return ext_to_platform.get(extension.lower())

    def generate_new_filename(
        self, media_item: Optional[MediaItem], original_filename: str
    ) -> str:
        """Generate a new filename for a game.

        Format: 'Game Title (Region) [Code].ext'

        Args:
            media_item: The media item (Game).
            original_filename: Original filename.

        Returns:
            New filename.
        """
        info = self.extract_info_from_filename(original_filename)
        extension = info["extension"]

        if not info["title"]:
            return original_filename

        title = format_name(info["title"])
        parts = [title]

        if info["region"]:
            parts.append(f"({info['region']})")
        elif info["regions"]:
            regions_str = ", ".join(info["regions"])
            parts.append(f"({regions_str})")

        if info["revision"]:
            parts.append(f"(Rev {info['revision']})")

        if info["version"]:
            parts.append(f"(v{info['version']})")

        if info["tags"]:
            parts.append(f"({', '.join(info['tags'])})")

        if info["release_code"]:
            parts.append(f"[{info['release_code']}]")

        new_name = " ".join(parts) + extension

        return new_name

    def organize_by_platform(
        self,
        source_path: str,
        dest_path: str,
        use_folder_structure: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Organize game files by platform.

        Created structure: Platform/Game.rom

        Args:
            source_path: Source folder.
            dest_path: Destination folder.
            use_folder_structure: Use folder structure to detect platform.
            dry_run: Simulation mode.

        Returns:
            Organization report.
        """
        report: Dict[str, Any] = {
            "moved": [],
            "errors": [],
            "total_files": 0,
            "total_moved": 0,
            "platforms": {},
        }

        for root, dirs, files in os.walk(source_path):
            for file in files:
                if not any(
                    file.lower().endswith(ext) for ext in self.supported_extensions
                ):
                    continue

                report["total_files"] += 1
                source_file = os.path.join(root, file)

                info = self.extract_info_from_filename(file)
                platform = info["platform"]

                if not platform:
                    platform = self.detect_platform_from_extension(info["extension"])

                if not platform and use_folder_structure:
                    path_parts = Path(source_file).parts
                    for part in path_parts:
                        part_lower = part.lower()
                        for platform_code, platform_name in self.PLATFORMS.items():
                            if platform_code in part_lower:
                                platform = platform_name
                                break
                        if platform:
                            break

                if not platform:
                    platform = "Unknown Platform"

                platform_folder = format_name(platform)
                dest_folder = os.path.join(dest_path, platform_folder)

                new_filename = self.generate_new_filename(None, file)
                dest_file = os.path.join(dest_folder, new_filename)

                if not dry_run:
                    try:
                        os.makedirs(dest_folder, exist_ok=True)
                        os.rename(source_file, dest_file)
                        report["moved"].append({"from": source_file, "to": dest_file})
                        report["total_moved"] += 1

                        platforms_dict: Dict[str, int] = report["platforms"]
                        if platform not in platforms_dict:
                            platforms_dict[platform] = 0
                        platforms_dict[platform] += 1
                    except OSError as e:
                        logger.exception(
                            "Game organize move failed for %s", source_file, exc_info=e
                        )
                        report["errors"].append({"file": source_file, "error": str(e)})
                else:
                    report["moved"].append({"from": source_file, "to": dest_file})
                    report["total_moved"] += 1

                    platforms_dict = report["platforms"]
                    if platform not in platforms_dict:
                        platforms_dict[platform] = 0
                    platforms_dict[platform] += 1

        return report

    def find_game_files(self, directory: str, recursive: bool = True) -> List[str]:
        """Find all game files in a directory.

        Args:
            directory: Directory to scan.
            recursive: Enable recursive search.

        Returns:
            List of game file paths.
        """
        return self.get_files_by_extension(
            directory, self.supported_extensions, recursive
        )

    def find_files(self, directory: str, recursive: bool = True) -> List[str]:
        """Unified alias for find_game_files."""
        return self.find_game_files(directory, recursive)
