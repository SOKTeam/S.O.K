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
"""Update dialog for application updates.

Displays release notes, download progress, and manages the update
installation process when a new version is available.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QHBoxLayout,
    QProgressBar,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QObject
from sok.core.updater import UpdateManager
from sok.ui.theme import Theme
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.i18n import tr
import webbrowser


class DownloadWorker(QObject):
    """Worker for downloading updates in a background thread.

    Emits progress updates and handles download/install process.

    Attributes:
        progress: Signal emitted with download percentage.
        finished: Signal emitted when download completes.
        error: Signal emitted with error message on failure.
    """

    progress = Signal(int)
    finished = Signal()
    error = Signal(str)

    def __init__(self, update_manager, url):
        """Initialize the download worker.

        Args:
            update_manager: UpdateManager instance for download handling.
            url: URL to download the update from.
        """
        super().__init__()
        self.manager = update_manager
        self.url = url
        self._running = True

    def stop(self):
        """Stop the download operation."""
        self._running = False

    def run(self):
        """Execute the download and install process.

        Downloads the update file and triggers installation.
        Emits finished on success, error on failure.
        """
        try:
            if not self._running:
                return
            self.manager.download_and_install(self.url, self._emit_progress)
            if self._running:
                self.finished.emit()
        except (OSError, ValueError) as e:
            self.error.emit(str(e))

    def _emit_progress(self, value: int):
        """Emit progress signal if worker is still running.

        Args:
            value: Progress percentage (0-100).
        """
        if self._running:
            self.progress.emit(value)


class UpdateDialog(QDialog):
    """Dialog for displaying update information and progress.

    Shows release notes and manages the download/install process.

    Attributes:
        update_manager: Manager for update operations.
        changelog: Text browser for release notes.
        progress_bar: Download progress indicator.
        btn_cancel: Cancel/ignore button.
        btn_update: Download and install button.
    """

    def __init__(
        self,
        parent=None,
        update_manager: UpdateManager | None = None,
        new_version: str = "",
    ):
        """Initialize the update dialog.

        Args:
            parent: Parent widget.
            update_manager: Manager for update operations.
            new_version: Version string of the available update.
        """
        super().__init__(parent)
        self.update_manager = update_manager
        self._runner = WorkerRunner(self)
        self.setWindowTitle(
            tr("update_available_title", "Update available: v{version}").format(
                version=new_version
            )
        )
        self.resize(500, 400)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel(
            tr(
                "update_available_header", "A new version (v{version}) is available!"
            ).format(version=new_version)
        )
        header.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {Theme.LIGHT['accent']};"
        )
        layout.addWidget(header)

        self.changelog = QTextBrowser()
        release_notes = (
            self.update_manager.get_release_notes() if self.update_manager else ""
        )
        self.changelog.setHtml(release_notes.replace("\n", "<br>"))
        self.changelog.setStyleSheet(
            """
            QTextBrowser {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 10px;
            }
        """
        )
        layout.addWidget(self.changelog)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                text-align: center;
                background-color: #1e1e1e;
                color: white;
            }}
            QProgressBar::chunk {{
                background-color: {Theme.LIGHT["accent"]};
                border-radius: 4px;
            }}
        """,
        )
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()

        self.btn_cancel = QPushButton(tr("ignore", "Ignore"))
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setStyleSheet(Theme.LIGHT["button_secondary"])

        self.btn_update = QPushButton(
            tr("download_and_install", "Download and Install")
        )
        self.btn_update.clicked.connect(self.start_update)
        self.btn_update.setStyleSheet(Theme.LIGHT["button_primary"])

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_update)

        layout.addLayout(btn_layout)

    def start_update(self):
        """Start the update download and installation process.

        Downloads the update if URL is an exe, otherwise opens
        the download page in a browser.
        """
        if not self.update_manager:
            return
        url = self.update_manager.get_download_url()
        if not url:
            QMessageBox.warning(
                self,
                tr("error", "Error"),
                tr("download_link_not_found", "Unable to find the download link."),
            )
            return

        if not url.endswith(".exe"):
            webbrowser.open(url)
            self.accept()
            return

        self.btn_update.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        worker = DownloadWorker(self.update_manager, url)
        self._runner.run(
            worker,
            lambda: self._on_download_finished(),
            self.on_error,
            self.progress_bar.setValue,
        )

    def _on_download_finished(self):
        """Handle successful download completion."""
        self.progress_bar.setValue(100)
        self.accept()

    def on_error(self, msg):
        """Handle download error.

        Shows error dialog and resets UI state.

        Args:
            msg: Error message to display.
        """
        QMessageBox.critical(
            self,
            tr("update_error", "Update error"),
            tr("download_failed", "Download failed:\n{msg}").format(msg=msg),
        )
        self.btn_update.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setVisible(False)

    def closeEvent(self, event):
        """Handle dialog close event.

        Stops any running download worker.

        Args:
            event: Close event.
        """
        self._runner.stop()
        super().closeEvent(event)
