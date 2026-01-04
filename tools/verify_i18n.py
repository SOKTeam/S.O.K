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
Verify i18n keys consistency.
Scans source code for tr("key", ...) calls and compares with JSON translation files.
"""

import re
import json
from pathlib import Path
from typing import Set, Dict


def scan_code_for_keys(src_dir: Path) -> Set[str]:
    """Scans Python files for tr("key", ...) patterns."""
    keys = set()
    pattern = re.compile(r'tr([\'"])(.+?)\1\s*[,)]')

    for path in src_dir.rglob("*.py"):
        try:
            content = path.read_text(encoding="utf-8")
            matches = pattern.findall(content)
            for match in matches:
                keys.add(match[1])
        except Exception as e:
            print(f"Error reading {path}: {e}")

    return keys


def load_translation_files(i18n_dir: Path) -> Dict[str, Set[str]]:
    """Loads all JSON files and returns keys for each language."""
    translations = {}
    for json_file in i18n_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                translations[json_file.name] = set(data.keys())
        except Exception as e:
            print(f"Error reading {json_file}: {e}")

    return translations


def main():
    root_dir = Path(__file__).resolve().parent.parent
    src_dir = root_dir / "src"
    i18n_dir = src_dir / "sok" / "resources" / "i18n"

    print("--- S.O.K i18n Verifier ---")
    print(f"Scanning source: {src_dir}")
    print(f"Scanning translations: {i18n_dir}\n")

    code_keys = scan_code_for_keys(src_dir)
    lang_keys = load_translation_files(i18n_dir)

    if not lang_keys:
        print("No translation files found!")
        return

    all_ok = True

    for lang_file, keys in lang_keys.items():
        missing = code_keys - keys
        extra = keys - code_keys

        print(f"[{lang_file}]")
        if not missing and not extra:
            print("All keys matched.")
        else:
            if missing:
                all_ok = False
                print(f"Missing keys ({len(missing)}):")
                for k in sorted(missing):
                    print(f"    - {k}")

            if extra:
                print(f"Unused/Extra keys ({len(extra)}):")
                for k in sorted(extra):
                    print(f"    - {k}")
        print()

    if all_ok:
        print("Perfect! All code keys are translated in all languages.")
    else:
        print("Some translations are missing. Please update your JSON files.")


if __name__ == "__main__":
    main()
