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
"""Shared UI state helpers (progress, empty state)."""

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


def set_progress(
    bar,
    label: QLabel,
    visible: bool,
    message: str | None = None,
    value: int | None = None,
):
    """Update progress bar and label visibility.

    Args:
        bar: Progress bar widget.
        label: Label widget for progress message.
        visible: Whether to show or hide the progress UI.
        message: Optional message text.
        value: Optional progress value (0-100).
    """
    bar.setVisible(visible)
    label.setVisible(visible)
    if value is not None:
        bar.setValue(value)
    if message is not None:
        label.setText(message)


def set_empty_state(layout, text: str) -> QLabel:
    """Add an empty state label to a layout.

    Args:
        layout: Layout to add the label to.
        text: Empty state message text.

    Returns:
        The created label widget.
    """
    empty = QLabel(text)
    empty.setObjectName("EmptyState")
    empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(empty)
    return empty
