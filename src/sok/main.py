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
Main entry point for S.O.K
Launches Qt GUI with modern interface
"""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from sok.ui.main_window import MainWindow
from sok.__version__ import __version__
from sok.core.security import check_security

# Add src to path if running from source to find sok package
sys.path.insert(0, str(Path(__file__).parent.parent))


# Detect if running as compiled executable (Nuitka)
IS_COMPILED = "__compiled__" in globals()


def get_app_data_dir() -> Path:
    """Get the application data directory (works in dev and compiled builds)."""
    if IS_COMPILED:
        # Running as compiled executable (Nuitka)
        return Path(sys.executable).parent
    else:
        # Running in development
        return Path(__file__).parent.parent.parent


def configure_logging():
    """Set up basic logging to console and rotating file."""
    if logging.getLogger().handlers:
        return

    log_level = os.getenv("SOK_LOG_LEVEL", "INFO").upper()
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "sok.log"

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logging.basicConfig(level=log_level, handlers=[file_handler, console_handler])


def main():
    """Launch the S.O.K application.

    Configures logging, performs security checks, and starts
    the Qt application with the main window.
    """
    configure_logging()
    check_security()
    app = QApplication(sys.argv)

    app.setApplicationName("S.O.K")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("S.O.K")

    icon_path = Path(__file__).parent / "resources" / "assets" / "logo.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
