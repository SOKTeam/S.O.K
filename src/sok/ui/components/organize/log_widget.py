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
Log/report widget for organization operations.

Displays progress messages and operation results.
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QFrame
from PySide6.QtCore import Qt, Signal

from sok.ui.components.base import Card
from sok.ui.theme import card_shadow
from sok.ui.i18n import tr

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log level for messages."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class LogEntry:
    """Log entry for organization operations.

    Attributes:
        message: The log message text.
        level: Severity level of the entry.
        details: Optional additional details.
    """

    message: str
    level: LogLevel
    details: Optional[str] = None


class OrganizeLogWidget(QWidget):
    """Log widget for organization operations.

    Displays progress, success, and error messages during file
    organization operations.

    Signals:
        entry_added: Emitted when a new log entry is added.
    """

    entry_added = Signal(LogEntry)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the log widget.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._entries: List[LogEntry] = []
        self._max_entries = 100
        self._build_ui()

    def _build_ui(self):
        """Build the log widget interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._title_label = QLabel(tr("log_title", "Journal"))
        self._title_label.setObjectName("SectionLabel")
        layout.addWidget(self._title_label)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setMaximumHeight(200)

        self._log_container = Card()
        self._log_container.setGraphicsEffect(card_shadow())
        self._log_layout = self._log_container._layout

        self._scroll.setWidget(self._log_container)
        layout.addWidget(self._scroll)

        self._empty_label = QLabel(tr("no_logs", "No operation in progress"))
        self._empty_label.setObjectName("EmptyState")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._log_layout.addWidget(self._empty_label)

    def _get_style_for_level(self, level: LogLevel) -> str:
        """Return the CSS style for a log level."""
        styles = {
            LogLevel.INFO: "color: #8E8E93;",
            LogLevel.SUCCESS: "color: #34C759;",
            LogLevel.WARNING: "color: #FF9500;",
            LogLevel.ERROR: "color: #FF3B30;",
        }
        return styles.get(level, "")

    def _get_prefix_for_level(self, level: LogLevel) -> str:
        """Return the prefix for a log level."""
        prefixes = {
            LogLevel.INFO: "ℹ️",
            LogLevel.SUCCESS: "✓",
            LogLevel.WARNING: "⚠️",
            LogLevel.ERROR: "✗",
        }
        return prefixes.get(level, "")

    def add_entry(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        details: Optional[str] = None,
    ):
        """Add an entry to the log.

        Args:
            message: Log message text.
            level: Severity level.
            details: Optional additional details.
        """
        self._empty_label.setVisible(False)

        entry = LogEntry(message=message, level=level, details=details)
        self._entries.append(entry)

        prefix = self._get_prefix_for_level(level)
        full_message = f"{prefix} {message}"
        if details:
            full_message += f"\n   {details}"

        label = QLabel(full_message)
        label.setStyleSheet(self._get_style_for_level(level))
        label.setWordWrap(True)
        self._log_layout.insertWidget(self._log_layout.count() - 1, label)

        self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        )

        if len(self._entries) > self._max_entries:
            self._entries.pop(0)
            item = self._log_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()  # type: ignore[union-attr]

        self.entry_added.emit(entry)

    def log_info(self, message: str, details: Optional[str] = None):
        """Add an information message.

        Args:
            message: Log message text.
            details: Optional additional details.
        """
        self.add_entry(message, LogLevel.INFO, details)

    def log_success(self, message: str, details: Optional[str] = None):
        """Add a success message.

        Args:
            message: Log message text.
            details: Optional additional details.
        """
        self.add_entry(message, LogLevel.SUCCESS, details)

    def log_warning(self, message: str, details: Optional[str] = None):
        """Add a warning message.

        Args:
            message: Log message text.
            details: Optional additional details.
        """
        self.add_entry(message, LogLevel.WARNING, details)

    def log_error(self, message: str, details: Optional[str] = None):
        """Add an error message.

        Args:
            message: Log message text.
            details: Optional additional details.
        """
        self.add_entry(message, LogLevel.ERROR, details)

    def log_report(self, report: Dict[str, Any]):
        """Add a complete operation report.

        Args:
            report: Report dictionary with total, success, and errors.
        """
        total = report.get("total", 0)
        success = report.get("success", 0)
        errors = report.get("errors", [])

        if errors:
            self.log_warning(
                tr(
                    "operation_completed_with_errors", "Operation completed with errors"
                ),
                f"{success}/{total} {tr('succeeded', 'succeeded')}, {len(errors)} {tr('errors', 'error(s)')}",
            )
            for error in errors[:5]:
                if isinstance(error, dict):
                    self.log_error(error.get("file", ""), error.get("error", ""))
                else:
                    self.log_error(str(error))
        else:
            self.log_success(
                tr("operation_completed", "Operation completed"),
                f"{success} {tr('files_processed', 'file(s) processed')}",
            )

    def clear(self):
        """Clear all log entries."""
        self._entries.clear()

        while self._log_layout.count() > 1:
            item = self._log_layout.takeAt(0)
            if item and item.widget() and item.widget() != self._empty_label:
                item.widget().deleteLater()  # type: ignore[union-attr]

        self._empty_label.setVisible(True)

    def get_entries(self) -> List[LogEntry]:
        """Return all log entries.

        Returns:
            Copy of the log entries list.
        """
        return self._entries.copy()

    def retranslate_ui(self):
        """Update texts after a language change."""
        self._title_label.setText(tr("log_title", "Log"))
        if self._empty_label.isVisible():
            self._empty_label.setText(tr("no_logs", "No operation in progress"))
