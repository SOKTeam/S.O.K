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
Input Components - Search bars, Combo boxes and Drop zones
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QLineEdit,
    QComboBox,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QListView,
    QStyledItemDelegate,
    QSizePolicy,
    QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QDragEnterEvent, QDropEvent, QFont

from sok.ui.theme import Theme, svg_icon
from sok.ui.i18n import tr
from sok.ui.components.base import parse_color


class ModernComboBox(QComboBox):
    """ComboBox with rounded popup support.

    A styled combo box that uses a QListView as its dropdown view
    with transparent background and no window shadow.
    """

    def __init__(self, parent=None):
        """Initialize the modern combo box.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setView(QListView())
        self.view().window().setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.view().window().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setItemDelegate(QStyledItemDelegate())


class SearchBar(QLineEdit):
    """Modern search bar input.

    A styled line edit with fixed height and placeholder text.
    """

    def __init__(self, placeholder: str = "", parent=None):
        """Initialize the search bar.

        Args:
            placeholder: Placeholder text. Defaults to translated "Search".
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setPlaceholderText(placeholder if placeholder else tr("search", "Search"))
        self.setFixedHeight(28)
        self.setObjectName("SearchBar")


class FileItemRow(QWidget):
    """Row representing a file in DropZone with remove button.

    Displays a folder icon, file name, and a remove button.

    Signals:
        removed: Emitted when the remove button is clicked, with the file path.
    """

    removed = Signal(Path)

    def __init__(self, path: Path, parent=None):
        """Initialize the file item row.

        Args:
            path: File path to display.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._path = path
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        folder_icon = svg_icon("folder", "#FFFFFF", 14)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(folder_icon)
        icon_lbl.setFixedSize(16, 16)
        layout.addWidget(icon_lbl)

        self.lbl = QLabel(path.name)
        self.lbl.setStyleSheet("color: white; font-size: 12px;")
        self.lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.lbl)

        btn = QPushButton("×")
        btn.setFixedSize(20, 20)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            """
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                color: white;
                font-weight: bold;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background: rgba(255, 75, 75, 0.8);
            }
        """
        )
        btn.clicked.connect(self._on_remove)
        layout.addWidget(btn)

        self.setStyleSheet(
            """
            FileItemRow {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 6px;
            }
        """
        )

    def _on_remove(self):
        """Handle remove button click."""
        self.removed.emit(self._path)

    def resizeEvent(self, event):
        """Handle widget resize by eliding text.

        Args:
            event: Resize event.
        """
        font_metrics = self.lbl.fontMetrics()
        avail_width = self.width() - 16 - 8 - 16 - 20 - 8 - 8
        if avail_width > 0:
            elided = font_metrics.elidedText(
                self._path.name, Qt.TextElideMode.ElideMiddle, avail_width
            )
            self.lbl.setText(elided)
        super().resizeEvent(event)


class DropZone(QFrame):
    """Drop zone for files and folders.

    A drag-and-drop area that accepts folder drops and displays
    selected folders as removable items.

    Signals:
        files_dropped: Emitted when files are dropped or selected.
    """

    files_dropped = Signal(list)

    def __init__(self, multi_select: bool = False, parent=None):
        """Initialize the drop zone.

        Args:
            multi_select: Allow multiple folder selection.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._files: list[Path] = []
        self._hover = False
        self._multi_select = multi_select
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("DropZone")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(4)
        self._update_ui()

    def get_path(self) -> Path | None:
        """Get the first selected path.

        Returns:
            First file path or None if empty.
        """
        return self._files[0] if self._files else None

    def get_paths(self) -> list:
        """Get all selected paths.

        Returns:
            Copy of the file paths list.
        """
        return self._files.copy()

    def clear(self):
        """Clear all selected files."""
        self._files = []
        self._update_ui()
        self.files_dropped.emit(self._files)

    def _update_ui(self):
        """Update the UI to reflect current files."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()  # type: ignore[union-attr]

        if not self._files:
            self.setMinimumHeight(90)
        else:
            self.setMinimumHeight(0)
            for f in self._files:
                row = FileItemRow(f)
                row.removed.connect(self._remove_file)
                self._layout.addWidget(row)

            if self._multi_select:
                add_btn = QPushButton(tr("add_folder", "+ Add Folder"))
                add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                add_btn.setStyleSheet(
                    """
                    QPushButton {
                        background: transparent;
                        color: rgba(255, 255, 255, 0.6);
                        border: 1px dashed rgba(255, 255, 255, 0.3);
                        border-radius: 4px;
                        padding: 4px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        color: white;
                        border-color: rgba(255, 255, 255, 0.6);
                        background: rgba(255, 255, 255, 0.05);
                    }
                """
                )
                add_btn.clicked.connect(self._open_dialog)
                self._layout.addWidget(add_btn)
        self.update()

    def _remove_file(self, path):
        """Remove a file from the selection.

        Args:
            path: Path to remove.
        """
        if path in self._files:
            self._files.remove(path)
            self._update_ui()
            self.files_dropped.emit(self._files)

    def _open_dialog(self):
        """Open the file selection dialog."""
        if self._multi_select:
            folder = QFileDialog.getExistingDirectory(
                self, tr("select_folder_dialog", "Add a folder")
            )
            if folder:
                path = Path(folder)
                if path.is_dir() and path not in self._files:
                    self._files.append(path)
                    self._update_ui()
                    self.files_dropped.emit(self._files)
        else:
            folder = QFileDialog.getExistingDirectory(
                self, tr("select_folder", "Dossier")
            )
            if folder:
                self._files = [Path(folder)]
                self._update_ui()
                self.files_dropped.emit(self._files)

    def dragEnterEvent(self, e: QDragEnterEvent):
        """Handle drag enter event.

        Args:
            e: Drag enter event.
        """
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._hover = True
            self.update()

    def dragLeaveEvent(self, e):
        """Handle drag leave event.

        Args:
            e: Drag leave event.
        """
        self._hover = False
        self.update()

    def dropEvent(self, e: QDropEvent):
        """Handle file drop event.

        Args:
            e: Drop event.
        """
        self._hover = False
        new_files = [
            Path(u.toLocalFile())
            for u in e.mimeData().urls()
            if Path(u.toLocalFile()).is_dir()
        ]
        if not new_files:
            return

        if self._multi_select:
            changed = False
            for f in new_files:
                if f not in self._files:
                    self._files.append(f)
                    changed = True
            if changed:
                self._update_ui()
                self.files_dropped.emit(self._files)
        else:
            self._files = new_files[:1]
            self._update_ui()
            self.files_dropped.emit(self._files)

    def mousePressEvent(self, e):
        """Handle mouse press to open dialog if empty.

        Args:
            e: Mouse event.
        """
        if not self._files:
            self._open_dialog()
        else:
            super().mousePressEvent(e)

    def paintEvent(self, e):
        """Paint the drop zone.

        Args:
            e: Paint event.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.window().c if hasattr(self.window(), "c") else Theme.DARK  # type: ignore[union-attr]
        rect = self.rect().adjusted(1, 1, -1, -1)

        bg_col = parse_color(c.get("input_bg", c["card"]))
        p.setBrush(bg_col)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, Theme.R, Theme.R)

        pen = p.pen()
        pen.setColor(
            parse_color(c["accent"]) if self._hover else parse_color(c["tertiary"])
        )
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.GlobalColor.transparent)
        p.drawRoundedRect(rect, Theme.R, Theme.R)

        if not self._files:
            p.setPen(parse_color(c["secondary"]))
            p.setFont(QFont(Theme.FONT, 12))
            p.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                tr("drag_drop_folder", "Glissez un dossier ou cliquez"),
            )
