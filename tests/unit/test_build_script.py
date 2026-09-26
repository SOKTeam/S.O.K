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
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from build_sok import require_env_file  # noqa: E402


class TestRequireEnvFile:
    def test_passes_when_env_exists(self, tmp_path):
        (tmp_path / ".env").write_text("API_KEY_TMDB_V4=x\n", encoding="utf-8")

        assert require_env_file(tmp_path, allow_missing=False) is True

    def test_stops_the_build_without_env(self, tmp_path):
        with pytest.raises(SystemExit, match="without its API keys"):
            require_env_file(tmp_path, allow_missing=False)

    def test_warns_when_missing_keys_are_allowed(self, tmp_path, capsys):
        assert require_env_file(tmp_path, allow_missing=True) is False
        assert "WITHOUT API keys" in capsys.readouterr().out
