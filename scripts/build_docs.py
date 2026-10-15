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
Build the developer documentation with Kiln.

The guides are the Markdown files in docs/ (configured by docs.yml). The API
reference is rendered by Kiln from api.json, a description of the package
that griffe writes from the source code. Kiln runs in Docker.

Usage:
    uv run --extra docs python scripts/build_docs.py          # Build into site/
    uv run --extra docs python scripts/build_docs.py serve    # Preview on http://localhost:4321
    uv run --extra docs python scripts/build_docs.py api      # Only write api.json
    uv run --extra docs python scripts/build_docs.py clean    # Remove site/ and api.json

Set KILN_IMAGE to try another Kiln image.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = PROJECT_ROOT / "site"
API_FILE = PROJECT_ROOT / "api.json"
KILN_IMAGE = os.environ.get("KILN_IMAGE", "ghcr.io/laidwin/kiln:v1")


def run_command(cmd: list[str]) -> int:
    """Run a command from the project root and return its exit code."""
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=PROJECT_ROOT)


def api() -> int:
    """Describe the sok package in api.json for the API reference.

    griffe reads the source without importing it. Modules left out of the
    reference are listed in docs.yml (api.exclude).
    """
    return run_command(
        [
            sys.executable,
            "-m",
            "griffe",
            "dump",
            "sok",
            "--search",
            "src",
            "--docstyle",
            "google",
            "--full",
            "--output",
            str(API_FILE),
        ]
    )


def kiln(command: str, *docker_args: str) -> int:
    """Run a Kiln command on the project in Docker."""
    return run_command(
        [
            "docker",
            "run",
            "--rm",
            *docker_args,
            "-v",
            f"{PROJECT_ROOT}:/project",
            KILN_IMAGE,
            command,
        ]
    )


def build() -> int:
    """Build the documentation into site/."""
    code = api() or kiln("build")
    if code == 0:
        print(f"Documentation built in {SITE_DIR}")
    return code


def serve() -> int:
    """Preview the documentation with live reload."""
    print("Preview on http://localhost:4321 (Ctrl+C to stop)")
    return api() or kiln("serve", "-p", "4321:4321")


def clean() -> int:
    """Remove the generated files."""
    if SITE_DIR.exists():
        print(f"Removing {SITE_DIR}")
        shutil.rmtree(SITE_DIR)
    if API_FILE.exists():
        print(f"Removing {API_FILE}")
        API_FILE.unlink()
    return 0


def main() -> int:
    commands = {"build": build, "serve": serve, "api": api, "clean": clean}
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"

    if cmd in ("-h", "--help"):
        print(__doc__)
        return 0
    if cmd not in commands:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(commands)}")
        return 1
    return commands[cmd]()


if __name__ == "__main__":
    sys.exit(main())
