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
from unittest.mock import MagicMock

from sok.ui.workers.base import BaseWorker


class BrokenWorker(BaseWorker):
    def execute(self):
        raise AttributeError("'Ops' object has no attribute 'organize_files_list'")


class TestBaseWorker:
    def test_unexpected_exception_emits_error(self, qtbot):
        """Any exception must reach the UI, otherwise it waits forever."""
        worker = BrokenWorker(config=MagicMock())
        errors = []
        worker.error.connect(errors.append)

        worker.run()

        assert errors == ["'Ops' object has no attribute 'organize_files_list'"]
