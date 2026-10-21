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
Media type detection worker for the files dropped on the home page.
"""

from pathlib import Path
from typing import List

from PySide6.QtCore import Signal

from sok.file_operations.detection import MediaTypeDetector
from sok.ui.workers.base import BaseWorker


class DetectionWorker(BaseWorker):
    """Scan dropped files and folders and sort them by media type.

    A large folder can take a while to scan, so it runs off the GUI thread.

    Signals:
        finished (DetectionReport): The groups, files to check and ignored files.
    """

    finished = Signal(object)

    def __init__(self, paths: List[Path], detector: MediaTypeDetector, config=None):
        """Initialize the detection worker.

        Args:
            paths: Dropped files and folders.
            detector: Detector to use.
            config: Configuration manager (uses default if None).
        """
        super().__init__(config)
        self._paths = paths
        self._detector = detector

    def execute(self):
        """Run the detection and emit the report."""
        self.finished.emit(self._detector.detect_sources(self._paths))
