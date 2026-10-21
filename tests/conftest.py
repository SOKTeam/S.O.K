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
import pytest

from sok.core import history


@pytest.fixture(autouse=True)
def rename_history(tmp_path, monkeypatch):
    """A rename history of its own for each test, never the user's one."""
    store = history.HistoryStore(tmp_path / "history.json")
    monkeypatch.setattr(history, "_history", store)
    return store
