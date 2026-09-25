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
"""Message boxes shown as sheets on macOS.

The functions mirror the QMessageBox static functions. Outside macOS they
call them unchanged; on macOS the box slides from the window title bar as
a sheet and shows the app icon instead of the generic information and
question icons.
"""

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QMessageBox, QWidget

from sok.ui.i18n import tr
from sok.ui.platform import IS_MACOS

StandardButton = QMessageBox.StandardButton
Icon = QMessageBox.Icon

# macOS alerts show the app icon, except for warnings and errors.
_APP_ICON_KINDS = (Icon.Information, Icon.Question, Icon.NoIcon)


def as_sheet(box: QMessageBox, parent: QWidget | None) -> None:
    """Show a message box as a sheet of the parent window (macOS only).

    Args:
        box: Message box, before exec() is called.
        parent: Widget whose window receives the sheet.
    """
    if not IS_MACOS or parent is None:
        return
    box.setParent(parent.window(), box.windowFlags())
    box.setWindowModality(Qt.WindowModality.WindowModal)
    app_icon = QGuiApplication.windowIcon()
    if box.icon() in _APP_ICON_KINDS and not app_icon.isNull():
        box.setIconPixmap(app_icon.pixmap(64, 64))


def _show(
    icon: Icon,
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: StandardButton,
    default: StandardButton,
    reveal: Path | None = None,
) -> StandardButton:
    box = QMessageBox(icon, title, text, buttons, parent)
    if default != StandardButton.NoButton:
        box.setDefaultButton(default)
    reveal_btn = None
    if reveal is not None:
        reveal_btn = box.addButton(
            tr("show_in_finder", "Show in Finder"),
            QMessageBox.ButtonRole.ActionRole,
        )
    as_sheet(box, parent)
    result = box.exec()
    if reveal_btn is not None and box.clickedButton() is reveal_btn:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(reveal)))
        return StandardButton.NoButton
    return StandardButton(result)


def information(
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: StandardButton = StandardButton.Ok,
    default: StandardButton = StandardButton.NoButton,
    reveal: Path | None = None,
) -> StandardButton:
    """Show an information message, like QMessageBox.information().

    Args:
        reveal: Folder to offer to show in the Finder (macOS only).
    """
    if not IS_MACOS:
        return QMessageBox.information(parent, title, text, buttons, default)
    return _show(Icon.Information, parent, title, text, buttons, default, reveal)


def warning(
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: StandardButton = StandardButton.Ok,
    default: StandardButton = StandardButton.NoButton,
    reveal: Path | None = None,
) -> StandardButton:
    """Show a warning message, like QMessageBox.warning().

    Args:
        reveal: Folder to offer to show in the Finder (macOS only).
    """
    if not IS_MACOS:
        return QMessageBox.warning(parent, title, text, buttons, default)
    return _show(Icon.Warning, parent, title, text, buttons, default, reveal)


def critical(
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: StandardButton = StandardButton.Ok,
    default: StandardButton = StandardButton.NoButton,
) -> StandardButton:
    """Show an error message, like QMessageBox.critical()."""
    if not IS_MACOS:
        return QMessageBox.critical(parent, title, text, buttons, default)
    return _show(Icon.Critical, parent, title, text, buttons, default)


def question(
    parent: QWidget | None,
    title: str,
    text: str,
    buttons: StandardButton = StandardButton.Yes | StandardButton.No,
    default: StandardButton = StandardButton.NoButton,
) -> StandardButton:
    """Ask a question, like QMessageBox.question()."""
    if not IS_MACOS:
        return QMessageBox.question(parent, title, text, buttons, default)
    return _show(Icon.Question, parent, title, text, buttons, default)
