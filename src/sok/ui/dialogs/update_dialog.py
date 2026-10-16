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
    QApplication,
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QHBoxLayout,
    QProgressBar,
)
from PySide6.QtCore import Qt, Signal, QObject
from sok.core.updater import UpdateManager, running_appimage
from sok.ui.components.base import ActionButton
from sok.ui.platform import IS_MACOS
from sok.ui.theme import Theme
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.i18n import tr
from sok.ui import message_box
import webbrowser

# Same height as ActionButton.
BUTTON_HEIGHT = 28 if IS_MACOS else 32


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
        # The colors of the main window theme (light, dark or orange).
        window = parent.window() if parent else None
        c = getattr(window, "c", None) or Theme.DARK

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel(
            tr(
                "update_available_header", "A new version (v{version}) is available!"
            ).format(version=new_version)
        )
        header.setObjectName("UpdateHeader")
        layout.addWidget(header)

        self.changelog = QTextBrowser()
        self.changelog.setOpenExternalLinks(True)
        release_notes = (
            self.update_manager.get_release_notes() if self.update_manager else ""
        )
        # GitHub release notes are Markdown.
        self.changelog.setMarkdown(release_notes)
        layout.addWidget(self.changelog)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()

        self.btn_cancel = QPushButton(tr("ignore", "Ignore"))
        self.btn_cancel.setObjectName("UpdateIgnoreBtn")
        self.btn_cancel.setFixedHeight(BUTTON_HEIGHT)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_update = ActionButton(
            tr("download_and_install", "Download and Install")
        )
        self.btn_update.clicked.connect(self.start_update)
        self.btn_update.setDefault(True)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_update)

        layout.addLayout(btn_layout)

        self.setStyleSheet(self._stylesheet(c))

    @staticmethod
    def _stylesheet(c: dict[str, str]) -> str:
        """Return the dialog stylesheet for a color palette.

        The dialog may open before the main window styles it (or outside
        it), so it sets its own colors, the primary button included.

        Args:
            c: Color palette of the current theme.
        """
        return f"""
            UpdateDialog {{
                background: {c["bg"]};
            }}
            QLabel {{
                color: {c["text"]};
            }}
            #UpdateHeader {{
                font-size: 16px;
                font-weight: bold;
            }}
            QTextBrowser {{
                background: {c.get("card_bg", c["card"])};
                color: {c["text"]};
                border: 1px solid {c["separator"]};
                border-radius: {Theme.R}px;
                padding: 10px;
            }}
            QProgressBar {{
                background: {c.get("input_bg", c["card"])};
                border: none;
                border-radius: 4px;
                color: {c["text"]};
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: {c["accent"]};
                border-radius: 4px;
            }}
            #ActionBtn {{
                background: {c["accent"]};
                color: {c["accent_text"]};
                border: none;
                border-radius: {BUTTON_HEIGHT // 2}px;
                font-weight: 600;
            }}
            #ActionBtn:disabled, #UpdateIgnoreBtn:disabled {{
                background: {c["separator"]};
                color: {c["secondary"]};
            }}
            #UpdateIgnoreBtn {{
                background: transparent;
                color: {c["text"]};
                border: 1px solid {c["separator"]};
                border-radius: {BUTTON_HEIGHT // 2}px;
                padding: 0 15px;
            }}
            #UpdateIgnoreBtn:hover {{
                background: {c["hover"]};
            }}
        """

    def start_update(self):
        """Start the update download and installation process.

        Downloads the update if URL is an exe, otherwise opens
        the download page in a browser.
        """
        if not self.update_manager:
            return
        url = self.update_manager.get_download_url()
        if not url:
            message_box.warning(
                self,
                tr("error", "Error"),
                tr("download_link_not_found", "Unable to find the download link."),
            )
            return

        if not url.lower().endswith((".exe", ".appimage")):
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
        """Handle successful download completion.

        The installer is running (on Linux the AppImage was replaced: start
        the new one), so quit to let it replace the app.
        """
        self.progress_bar.setValue(100)
        self.accept()
        if running_appimage():
            UpdateManager.restart_appimage()
        QApplication.quit()

    def on_error(self, msg):
        """Handle download error.

        Shows error dialog and resets UI state.

        Args:
            msg: Error message to display.
        """
        message_box.critical(
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
