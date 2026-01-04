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
"""Shared UI helpers for pages (labels, empty states)."""

from PySide6.QtWidgets import QLabel


def make_section_label(tr_key: str, default: str) -> QLabel:
    """Create a styled section label.

    Args:
        tr_key: Translation key for the label.
        default: Default label text.

    Returns:
        QLabel with section styling and translation properties.
    """
    lbl = QLabel()
    lbl.setObjectName("SectionLabel")
    lbl.setProperty("tr_key", tr_key)
    lbl.setProperty("tr_default", default)
    return lbl
