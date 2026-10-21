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

from sok.config import config_manager
from sok.config.api_registry import get_all_env_vars


@pytest.fixture(autouse=True)
def config_folder(tmp_path, monkeypatch):
    """Settings of their own for each test, never the user's ones."""
    folder = tmp_path / "config"
    monkeypatch.setenv("SOK_CONFIG_DIR", str(folder))
    monkeypatch.setattr(config_manager, "load_dotenv", lambda *a, **k: None)
    for variable in get_all_env_vars().values():
        monkeypatch.delenv(variable, raising=False)
    for name in ("SOK_AUTH", "SOK_USERNAME", "SOK_PASSWORD", "SOK_ENV_KEYS_WIN"):
        monkeypatch.delenv(name, raising=False)
    config_manager.reset_config_manager()
    yield folder
    config_manager.reset_config_manager()
