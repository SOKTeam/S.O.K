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
Convert Qt Designer .ui files to Python.
Usage: python build_ui.py
"""

import subprocess
from pathlib import Path
import sys


def convert_ui_files():
    """Convert all .ui files to Python files."""
    ui_designer_dir = Path(__file__).parent / "ui" / "designer"
    ui_generated_dir = Path(__file__).parent / "ui" / "generated"

    if not ui_designer_dir.exists():
        print(f"Directory {ui_designer_dir} does not exist")
        return 1

    ui_files = list(ui_designer_dir.glob("*.ui"))

    if not ui_files:
        print(f"No .ui files found in {ui_designer_dir}")
        return 0

    print(f"Converting {len(ui_files)} .ui file(s)...\n")

    errors = []

    for ui_file in ui_files:
        py_file = ui_generated_dir / f"ui_{ui_file.stem}.py"
        print(f"Converting {ui_file.name} → {py_file.name}")

        try:
            subprocess.run(
                ["pyside6-uic", str(ui_file), "-o", str(py_file)],
                capture_output=True,
                text=True,
                check=True,
            )
            print("Success")

        except subprocess.CalledProcessError as e:
            print(f"Error: {e.stderr}")
            errors.append((ui_file.name, e.stderr))

        except FileNotFoundError:
            print("pyside6-uic not found. Install PySide6: pip install PySide6")
            return 1

    print("\n" + "=" * 50)

    if errors:
        print(f"{len(errors)} error(s) encountered:")
        for filename, error in errors:
            print(f"   - {filename}: {error}")
        return 1
    else:
        print("All files converted successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(convert_ui_files())
