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
from sok.config.config_manager import log_dir
from sok.core.desktop_entry import install_desktop_entry
from sok.ui.theme import APP_ICON, load_bundled_fonts

# Add src to path if running from source to find sok package
sys.path.insert(0, str(Path(__file__).parent.parent))


def configure_logging():
    """Set up basic logging to console and rotating file."""
    if logging.getLogger().handlers:
        return

    log_level = os.getenv("SOK_LOG_LEVEL", "INFO").upper()
    folder = log_dir()
    folder.mkdir(parents=True, exist_ok=True)
    log_file = folder / "sok.log"

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

    if sys.platform.startswith("linux"):
        # Wayland matches the window to its .desktop file (dock icon, name)
        # by this id: packaging/linux/com.sokteam.sok.desktop.
        app.setDesktopFileName("com.sokteam.sok")
        install_desktop_entry()
        load_bundled_fonts()
        icon_path = APP_ICON
    else:
        icon_name = "logo.icns" if sys.platform == "darwin" else "logo.ico"
        icon_path = Path(__file__).parent / "resources" / "assets" / icon_name
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
