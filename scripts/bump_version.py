#!/usr/bin/env python3
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
Keep the application version identical in every file that stores it.

pyproject.toml is the source of truth. Usage:
    python scripts/bump_version.py 1.2.0   # write 1.2.0 everywhere
    python scripts/bump_version.py --check # fail if a file is out of sync

Called by semantic-release (see .releaserc.json) and by the CI.
"""

import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# File -> pattern whose "version" group holds the version.
VERSION_FILES = {
    "pyproject.toml": r'(?ms)^\[project\]$.*?^version = "(?P<version>[^"]*)"',
    "src/sok/__version__.py": r'(?m)^__version__ = "(?P<version>[^"]*)"',
    "uv.lock": r'(?m)^name = "sok"\nversion = "(?P<version>[^"]*)"',
}

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def read_version(path: str) -> str:
    """Return the version stored in a file."""
    content = (ROOT_DIR / path).read_text(encoding="utf-8")
    match = re.search(VERSION_FILES[path], content)
    if not match:
        sys.exit(f"Version not found in {path}")
    return match.group("version")


def write_version(path: str, version: str) -> None:
    """Replace the version stored in a file."""
    file = ROOT_DIR / path
    content = file.read_text(encoding="utf-8")
    match = re.search(VERSION_FILES[path], content)
    if not match:
        sys.exit(f"Version not found in {path}")
    start, end = match.span("version")
    file.write_text(content[:start] + version + content[end:], encoding="utf-8")


def check() -> None:
    """Exit with an error if a file does not match pyproject.toml."""
    expected = read_version("pyproject.toml")
    mismatches = [
        f"  {path}: {found} (expected {expected})"
        for path in VERSION_FILES
        if (found := read_version(path)) != expected
    ]
    if mismatches:
        print("Version mismatch:\n" + "\n".join(mismatches))
        print(f"Run: python scripts/bump_version.py {expected}")
        sys.exit(1)
    print(f"Version {expected} is consistent in {len(VERSION_FILES)} files.")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    if arg == "--check":
        check()
        return
    if not SEMVER.match(arg):
        sys.exit(f"Invalid version: {arg} (expected X.Y.Z)")
    for path in VERSION_FILES:
        write_version(path, arg)
        print(f"{path}: {arg}")


if __name__ == "__main__":
    main()
