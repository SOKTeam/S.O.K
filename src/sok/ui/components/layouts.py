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
FlowLayout for responsive widgets using PySide6
Based on Qt Official Example
"""

from PySide6.QtWidgets import QLayout
from PySide6.QtCore import Qt, QRect, QSize


class FlowLayout(QLayout):
    """Flow layout for responsive widget arrangement.

    A custom layout that arranges widgets in a flow pattern,
    wrapping to new lines when the width is exceeded. Based on
    the Qt official flow layout example.
    """

    def __init__(self, parent=None, margin=0, spacing=-1):
        """Initialize the flow layout.

        Args:
            parent: Parent widget.
            margin: Margin around the layout.
            spacing: Spacing between items (-1 for default).
        """
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._items = []

    def __del__(self):
        """Clean up items on deletion."""
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        """Add an item to the layout.

        Args:
            item: Layout item to add.
        """
        self._items.append(item)

    def count(self):
        """Get the number of items.

        Returns:
            Number of items in the layout.
        """
        return len(self._items)

    def itemAt(self, index):
        """Get item at index.

        Args:
            index: Item index.

        Returns:
            Item at index or None.
        """
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        """Remove and return item at index.

        Args:
            index: Item index.

        Returns:
            Removed item or None.
        """
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        """Get expanding directions.

        Returns:
            Zero (no expanding).
        """
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        """Check if height depends on width.

        Returns:
            True, height depends on width.
        """
        return True

    def heightForWidth(self, width):
        """Calculate height for given width.

        Args:
            width: Available width.

        Returns:
            Required height.
        """
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        """Set the layout geometry.

        Args:
            rect: New geometry rectangle.
        """
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        """Get the size hint.

        Returns:
            Minimum size as hint.
        """
        return self.minimumSize()

    def minimumSize(self):
        """Calculate minimum size.

        Returns:
            Minimum size required by items.
        """
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        size += QSize(
            2 * self.contentsMargins().top(), 2 * self.contentsMargins().top()
        )
        return size

    def _do_layout(self, rect, test_only):
        """Perform the layout calculation.

        Args:
            rect: Available rectangle.
            test_only: If True, only calculate without applying.

        Returns:
            Total height used.
        """
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        rows = []
        current_row = []
        current_row_width = 0

        for item in self._items:
            size = item.sizeHint()
            w = size.width()
            h = size.height()

            if current_row and (current_row_width + w + spacing > rect.width()):
                rows.append((current_row, current_row_width, line_height))
                current_row = []
                current_row_width = 0
                line_height = 0

            current_row.append(item)
            current_row_width += w + spacing
            line_height = max(line_height, h)

        if current_row:
            rows.append((current_row, current_row_width, line_height))

        y_off = y

        for row_items, row_width, row_height in rows:
            if not row_items:
                continue

            actual_used_width = row_width - spacing

            available_width = rect.width()
            extra_space = max(0, available_width - actual_used_width)

            add_per_item = extra_space / len(row_items)

            x_off = x
            for item in row_items:
                w = item.sizeHint().width() + add_per_item
                h = row_height

                if not test_only:
                    item.setGeometry(QRect(int(x_off), int(y_off), int(w), int(h)))

                x_off += w + spacing

            y_off += row_height + spacing

        return y_off - rect.y()
