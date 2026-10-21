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
Undo Worker: puts the files of a rename back, off the GUI thread.
"""

from typing import Optional

from PySide6.QtCore import Signal

from sok.core.history import get_history
from sok.ui.workers.base import BaseWorker


class UndoWorker(BaseWorker):
    """Worker that undoes an operation of the rename history.

    Moving files back can take a while across drives.

    Signals:
        finished (object): The UndoReport.
    """

    finished = Signal(object)

    def __init__(self, operation_id: str, index: Optional[int] = None, config=None):
        """Initialize the worker.

        Args:
            operation_id: The operation to undo.
            index: One file of it (its position), or None for all.
            config: Optional ConfigManager.
        """
        super().__init__(config)
        self._operation_id = operation_id
        self._index = index

    def execute(self):
        """Put the files back."""
        self.finished.emit(get_history().undo(self._operation_id, self._index))
