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
"""Helpers for OrganizePage preview/detection logic."""

from pathlib import Path
from typing import List, Tuple, Optional

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt

from sok.ui.components.preview import FileRow


class OrganizePreviewController:
    """Encapsulates file preview detection and construction.

    Handles extracting media information from filenames and
    building preview rows for the organization UI.
    """

    def __init__(self, ops, tr_fn, max_preview_files: int = 15):
        """Initialize the preview controller.

        Args:
            ops: Operations handler with extract_info_from_filename method.
            tr_fn: Translation function.
            max_preview_files: Maximum files to show in preview.
        """
        self._ops = ops
        self._tr = tr_fn
        self._max_preview_files = max_preview_files

    def detect_query_and_type(
        self, file_name: str, media_type: str
    ) -> Tuple[str, Optional[str]]:
        """Detect search query and content type from filename.

        Args:
            file_name: Name of the file to analyze.
            media_type: Type of media ('video', 'music', 'book', 'game').

        Returns:
            Tuple of (detected query, detected content type).
        """
        detected_query = ""
        detected_type = None
        if not hasattr(self._ops, "extract_info_from_filename"):
            return detected_query, detected_type

        info = self._ops.extract_info_from_filename(file_name)
        if media_type == "video":
            detected_query = info.get("title", "")
            detected_type = info.get("type", "")
        elif media_type == "music":
            artist = info.get("artist", "")
            album = info.get("album", "")
            if artist and album:
                detected_query = f"{artist} {album}"
                detected_type = "album"
            elif artist:
                detected_query = artist
                detected_type = "artist"
            else:
                detected_query = info.get("title", "")
        elif media_type == "book":
            detected_query = info.get("title", "")
            if info.get("author"):
                detected_query = f"{info['title']} {info['author']}"
        elif media_type == "game":
            detected_query = info.get("title", "")
        return detected_query, detected_type

    def build_preview(
        self, files: List[Path]
    ) -> Tuple[List[Tuple[Path, FileRow]], Optional[QLabel]]:
        """Build preview rows for files.

        Args:
            files: List of file paths to preview.

        Returns:
            Tuple of (list of (path, FileRow) tuples, optional "more" label).
        """
        file_rows: List[Tuple[Path, FileRow]] = []
        for f in files[: self._max_preview_files]:
            info = {}
            if hasattr(self._ops, "extract_info_from_filename"):
                info = self._ops.extract_info_from_filename(f.name)
            row = FileRow(f.name, "", info)
            file_rows.append((f, row))

        more_label: Optional[QLabel] = None
        if len(files) > self._max_preview_files:
            more_label = QLabel(
                f"+ {len(files) - self._max_preview_files} {self._tr('others', 'others')}..."
            )
            more_label.setObjectName("EmptyState")
            more_label.setFixedHeight(28)
            more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        return file_rows, more_label
