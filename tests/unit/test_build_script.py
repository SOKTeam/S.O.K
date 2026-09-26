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
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from build_sok import (  # noqa: E402
    declared_constants,
    inject_env_vars,
    require_env_file,
)


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


class TestInjectEnvVars:
    @pytest.fixture
    def sok_dir(self, tmp_path):
        core = tmp_path / "sok" / "core"
        core.mkdir(parents=True)
        shutil.copy(ROOT / "src" / "sok" / "core" / "constants.py", core)
        return tmp_path / "sok"

    def test_declared_constants_lists_the_app_keys(self):
        source = (ROOT / "src" / "sok" / "core" / "constants.py").read_text(
            encoding="utf-8"
        )

        names = declared_constants(source)

        assert {"API_KEY_TMDB_V4", "IGDB_CLIENT_SECRET", "CHECK_UPDATES"} <= names
        assert "_K" not in names

    def test_injects_only_the_keys_the_app_reads(self, tmp_path, sok_dir):
        (tmp_path / ".env").write_text(
            "# comment\r\nAPI_KEY_TMDB_V4=tmdb-key\r\nGITHUB_TOKEN=secret\r\n",
            encoding="utf-8",
        )

        assert inject_env_vars(sok_dir, tmp_path) is True

        namespace = {}
        exec((sok_dir / "core" / "constants.py").read_text(encoding="utf-8"), namespace)
        constants = namespace["Constants"]
        assert constants.get("API_KEY_TMDB_V4") == "tmdb-key"
        assert not hasattr(constants, "GITHUB_TOKEN")
