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


class QuotaWorker(BaseWorker):
    def execute(self):
        from sok.core.exceptions import APIRateLimitError

        raise APIRateLimitError("HTTP 429: Quota exceeded", "google_books")


def test_api_error_emits_a_translated_message(qtbot):
    from sok.ui.errors import error_message
    from sok.core.exceptions import APIRateLimitError

    worker = QuotaWorker(config=MagicMock())
    with qtbot.waitSignal(worker.error) as signal:
        worker.run()

    expected = error_message(APIRateLimitError("x", "google_books"))
    assert signal.args == [expected]
    assert "Google Books" in expected
