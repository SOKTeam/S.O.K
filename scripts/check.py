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
Pre-push quality checks for S.O.K.

Run all code quality checks before pushing to ensure CI will pass.
Usage: python scripts/check.py [--fast]
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_section(message: str) -> None:
    """Print a formatted section header."""
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{message}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{'=' * 60}{Colors.ENDC}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.OKBLUE}ℹ {message}{Colors.ENDC}")


def run_command(
    command: List[str], description: str, step: int, total: int
) -> Tuple[bool, float]:
    """
    Run a shell command and return success status.

    Args:
        command: Command and arguments to run
        description: Human-readable description of the check
        step: Current step number
        total: Total number of steps

    Returns:
        Tuple of (success: bool, duration: float)
    """
    print_info(f"[{step}/{total}] {description}...")

    start_time = time.time()

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        duration = time.time() - start_time

        if result.returncode == 0:
            print_success(f"{description} passed ({duration:.2f}s)")
            return True, duration
        else:
            print_error(f"{description} failed ({duration:.2f}s)")
            if result.stdout:
                print(f"\n{Colors.WARNING}STDOUT:{Colors.ENDC}")
                print(result.stdout)
            if result.stderr:
                print(f"\n{Colors.WARNING}STDERR:{Colors.ENDC}")
                print(result.stderr)
            return False, duration

    except FileNotFoundError:
        duration = time.time() - start_time
        print_error(f"Command not found: {command[0]}")
        print_info("Make sure all dependencies are installed: uv sync")
        return False, duration
    except Exception as e:
        duration = time.time() - start_time
        print_error(f"Unexpected error: {e}")
        return False, duration


def check_project_root() -> bool:
    """Verify we're running from the project root."""
    required_files = ["pyproject.toml", "src"]

    for item in required_files:
        if not Path(item).exists():
            print_error(f"Not in project root: {item} not found")
            print_info("Run this script from the project root directory")
            return False

    return True


def main() -> int:
    """Run all quality checks."""
    # Parse arguments
    fast_mode = "--fast" in sys.argv

    # Header
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║         S.O.K Code Quality Checks                         ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")

    if fast_mode:
        print_info("Running in FAST mode (skipping tests)")

    # Verify we're in the project root
    if not check_project_root():
        return 1

    # Define checks
    checks = [
        (["uv", "run", "ruff", "check", "."], "🔍 Linting with Ruff"),
        (
            ["uv", "run", "ruff", "format", "--check", "."],
            "🎨 Checking code formatting",
        ),
        (
            ["uv", "run", "mypy", "src/sok", "--ignore-missing-imports"],
            "🔎 Type checking with MyPy",
        ),
        (["uv", "run", "ty", "check", "src", "tests"], "🔎 Type checking with Ty"),
    ]

    # Add tests if not in fast mode
    if not fast_mode:
        checks.append(
            (
                ["uv", "run", "pytest", "tests/", "-v", "--tb=short"],
                "🧪 Running tests with Pytest",
            )
        )

    # Run all checks
    total_checks = len(checks)
    results = []
    total_duration = 0.0

    for i, (command, description) in enumerate(checks, 1):
        success, duration = run_command(command, description, i, total_checks)
        results.append((description, success, duration))
        total_duration += duration

        # Stop on first failure
        if not success:
            break

    # Summary
    print_section("📊 Summary")

    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed

    print(f"Total checks: {len(results)}")
    print(f"Passed: {Colors.OKGREEN}{passed}{Colors.ENDC}")
    print(f"Failed: {Colors.FAIL}{failed}{Colors.ENDC}")
    print(f"Duration: {total_duration:.2f}s")

    # Detailed results
    if results:
        print(f"\n{Colors.BOLD}Details:{Colors.ENDC}")
        for description, success, duration in results:
            status = (
                f"{Colors.OKGREEN}✓{Colors.ENDC}"
                if success
                else f"{Colors.FAIL}✗{Colors.ENDC}"
            )
            print(f"  {status} {description} ({duration:.2f}s)")

    # Final message
    print()
    if failed == 0:
        print(
            f"{Colors.OKGREEN}{Colors.BOLD}╔═══════════════════════════════════════╗{Colors.ENDC}"
        )
        print(
            f"{Colors.OKGREEN}{Colors.BOLD}║  ✓ All checks passed! Ready to push  ║{Colors.ENDC}"
        )
        print(
            f"{Colors.OKGREEN}{Colors.BOLD}╚═══════════════════════════════════════╝{Colors.ENDC}"
        )
        return 0
    else:
        print(
            f"{Colors.FAIL}{Colors.BOLD}╔═══════════════════════════════════════╗{Colors.ENDC}"
        )
        print(
            f"{Colors.FAIL}{Colors.BOLD}║  ✗ Some checks failed. Fix required  ║{Colors.ENDC}"
        )
        print(
            f"{Colors.FAIL}{Colors.BOLD}╚═══════════════════════════════════════╝{Colors.ENDC}"
        )
        print()
        print_info("Fix the errors above and run the checks again")
        return 1


if __name__ == "__main__":
    sys.exit(main())
