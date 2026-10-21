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
import os
import subprocess
import sys

# Imports every module but the desktop ones with the desktop extra blocked,
# as in the S.O.K Server image, which has no Qt.
SCRIPT = """
import importlib, pkgutil, sys

class Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in ("PySide6", "shiboken6", "pypresence"):
            raise ImportError(f"{name} is a desktop dependency")
        return None

sys.meta_path.insert(0, Blocker())
import sok

failed = []
for module in pkgutil.walk_packages(sok.__path__, "sok."):
    if module.name.startswith("sok.ui") or module.name == "sok.main":
        continue
    try:
        importlib.import_module(module.name)
    except Exception as exc:
        failed.append(f"{module.name}: {exc!r}")
print("\\n".join(failed))
sys.exit(1 if failed else 0)
"""


def test_the_core_runs_without_the_desktop_dependencies(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        capture_output=True,
        text=True,
        env={**os.environ, "SOK_CONFIG_DIR": str(tmp_path)},
    )

    assert result.returncode == 0, result.stdout + result.stderr
