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
Build MkDocs documentation.

Usage:
    python scripts/build_docs.py          # Build docs
    python scripts/build_docs.py serve    # Start dev server
    python scripts/build_docs.py clean    # Clean site folder
"""

import subprocess
import sys
import shutil
from pathlib import Path


# Racine du projet
PROJECT_ROOT = Path(__file__).parent.parent
SITE_DIR = PROJECT_ROOT / "site"


def run_command(cmd: list[str]) -> int:
    """Executes a command and returns the exit code."""
    print(f"{' '.join(cmd)}")
    return subprocess.call(cmd, cwd=PROJECT_ROOT)


def build():
    """Build the documentation."""
    print("Building documentation...")
    code = run_command(["mkdocs", "build"])
    if code == 0:
        print(f"Documentation built in {SITE_DIR}")
    else:
        print("Build failed")
    return code


def serve():
    """Starts the development server."""
    print("Starting dev server on http://127.0.0.1:8000")
    print("Press Ctrl+C to stop\n")
    return run_command(["mkdocs", "serve"])


def clean():
    """Cleans the build folder."""
    if SITE_DIR.exists():
        print(f"Removing {SITE_DIR}...")
        shutil.rmtree(SITE_DIR)
        print("Cleaned")
    else:
        print("Nothing to clean")
    return 0


def main():
    commands = {
        "build": build,
        "serve": serve,
        "clean": clean,
    }

    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"

    if cmd in ["-h", "--help"]:
        print(__doc__)
        return 0

    if cmd not in commands:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(commands.keys())}")
        return 1

    return commands[cmd]()


if __name__ == "__main__":
    sys.exit(main())
