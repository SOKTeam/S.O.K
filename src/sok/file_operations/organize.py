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
Organization of a list of files selected in the UI.

This module provides the FileListOrganizerMixin used by the music, book
and game file operations. Video has its own implementation, which handles
season folders.
"""

import os
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from sok.config.config_manager import get_config_manager
from sok.core.interfaces import MediaItem
from sok.file_operations.base_operations import make_folders, move_file

logger = logging.getLogger(__name__)


class FileListOrganizerMixin:
    """Move a list of files into the folder structure of a media item.

    Requires the class to provide generate_new_filename(media_item, filename).
    """

    def get_destination_folders(self, media_item: Optional[MediaItem]) -> List[str]:
        """Return the folders to create under the destination path.

        Args:
            media_item: The selected media item, or None.

        Returns:
            Folder names from the destination root to the file location.
        """
        if media_item is None:
            return []
        return media_item.get_folder_structure()

    def batch_target(
        self, media_item: MediaItem, file_path: Path, alone: bool
    ) -> Tuple[List[str], str]:
        """Folders and file name of one file of a batch.

        Args:
            media_item: The media item of the file.
            file_path: The file.
            alone: False when the item has other files in the batch, such
                as the .bin of a .cue.

        Returns:
            The folders under the destination, and the new file name.
        """
        return (
            self.get_destination_folders(media_item),
            self.generate_new_filename(media_item, file_path.name),  # type: ignore[attr-defined]
        )

    def organize_items_batch(
        self,
        mappings: List[Tuple[Path, MediaItem]],
        dest_path: str,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, Any]:
        """Organize files that each have their own media item.

        Each file goes where batch_target() says: by default the folder
        structure of its item, under the name generate_new_filename() gives.
        A batch of books, each with its own book, for instance. The files of
        one item share the same media item object.

        Args:
            mappings: (file, media item) pairs.
            dest_path: Destination folder.
            dry_run: If True, simulate without making changes.
            progress_callback: Function called with (current, total, filename).

        Returns:
            Organization report, as organize_files_list() returns.
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
            "total_files": len(mappings),
            "total_moved": 0,
        }

        files_per_item: Dict[int, int] = {}
        for _, media_item in mappings:
            files_per_item[id(media_item)] = files_per_item.get(id(media_item), 0) + 1

        for idx, (file_path, media_item) in enumerate(mappings):
            source_file = str(file_path)
            if progress_callback:
                progress_callback(idx + 1, len(mappings), file_path.name)

            folders, new_filename = self.batch_target(
                media_item, file_path, files_per_item[id(media_item)] == 1
            )
            dest_folder = os.path.join(dest_path, *folders)
            dest_file = os.path.join(dest_folder, new_filename)

            if skip_duplicates and os.path.exists(dest_file):
                report["skipped"].append(
                    {"file": source_file, "reason": "File already exists"}
                )
                continue

            if dry_run:
                report["moved"].append({"from": source_file, "to": dest_file})
                report["total_moved"] += 1
                continue

            try:
                if not os.path.exists(dest_folder):
                    if not create_folders:
                        report["errors"].append(
                            {
                                "file": source_file,
                                "error": "Missing folder and creation disabled",
                            }
                        )
                        continue
                    make_folders(dest_folder)
                backup_path = move_file(
                    source_file, dest_file, backup=backup_before_rename
                )
                if backup_path and log_operations:
                    logger.info("Backup created: %s", backup_path)
                report["moved"].append({"from": source_file, "to": dest_file})
                report["total_moved"] += 1
                if log_operations:
                    logger.info("Moved: %s -> %s", source_file, dest_file)
            except OSError as e:
                logger.exception("Batch move failed for %s", source_file, exc_info=e)
                report["errors"].append({"file": source_file, "error": str(e)})

        return report

    def organize_files_list(
        self,
        files: List[Path],
        dest_path: str,
        media_item: Optional[MediaItem],
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Dict[str, Any]:
        """Organize a list of files into the media item's folder structure.

        Args:
            files: List of files to organize.
            dest_path: Destination folder.
            media_item: The selected media item. If None, files are renamed
                and moved directly into dest_path.
            dry_run: If True, simulate without making changes.
            progress_callback: Function called with (current, total, filename).

        Returns:
            Organization report.
        """
        if media_item is not None:
            # Each file of the item may go to its own folder and name (see
            # batch_target): the tracks of an album named from their tags.
            return self.organize_items_batch(
                [(Path(f), media_item) for f in files],
                dest_path,
                dry_run=dry_run,
                progress_callback=progress_callback,
            )

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

        dest_folder = os.path.join(dest_path, *self.get_destination_folders(media_item))

        if not dry_run and not os.path.exists(dest_folder):
            if not create_folders:
                report["errors"].append(
                    {
                        "file": dest_folder,
                        "error": "Missing folder and creation disabled",
                    }
                )
                return report
            make_folders(dest_folder)

        for idx, file_path in enumerate(files):
            file = file_path.name
            source_file = str(file_path)

            if progress_callback:
                progress_callback(idx + 1, len(files), file)

            new_filename = self.generate_new_filename(media_item, file)  # type: ignore[attr-defined]
            dest_file = os.path.join(dest_folder, new_filename)

            if skip_duplicates and os.path.exists(dest_file):
                report["skipped"].append(
                    {"file": source_file, "reason": "File already exists"}
                )
                if log_operations:
                    logger.info("Skipped duplicate: %s", source_file)
                continue

            if dry_run:
                report["moved"].append({"from": source_file, "to": dest_file})
                report["total_moved"] += 1
                continue

            try:
                backup_path = move_file(
                    source_file, dest_file, backup=backup_before_rename
                )
                if backup_path and log_operations:
                    logger.info("Backup created: %s", backup_path)
                report["moved"].append({"from": source_file, "to": dest_file})
                report["total_moved"] += 1
                if log_operations:
                    logger.info("Moved: %s -> %s", source_file, dest_file)
            except OSError as e:
                logger.exception(
                    "Organize list move failed for %s", source_file, exc_info=e
                )
                report["errors"].append({"file": source_file, "error": str(e)})

        return report
