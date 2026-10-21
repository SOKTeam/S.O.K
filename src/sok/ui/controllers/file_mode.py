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
"""Check, before a rename, that the hard links of the file mode can be made."""

import os
from pathlib import Path
from typing import Iterable, Optional

from PySide6.QtWidgets import QMessageBox, QWidget

from sok.config.config_manager import get_config_manager
from sok.core.history import LINK
from sok.file_operations.base_operations import can_hard_link
from sok.ui import message_box
from sok.ui.i18n import tr


def link_problem(files: Iterable[Path], dest: str) -> Optional[Path]:
    """The first folder whose files cannot be hard linked into dest, if any.

    One test link per drive of the files is enough.
    """
    tested = set()
    for file in files:
        try:
            device = os.stat(file).st_dev
        except OSError:
            continue
        if device in tested:
            continue
        tested.add(device)
        if not can_hard_link(str(file), dest):
            return Path(file).parent
    return None


def hard_link_blocked(parent: QWidget, files: Iterable[Path], dest: str) -> bool:
    """Tell the user and return True when the file mode is a hard link that
    cannot be made, before anything is renamed."""
    if get_config_manager().get("file_mode") != LINK:
        return False
    folder = link_problem(files, dest)
    if folder is None:
        return False
    # The title, which macOS does not show on a sheet, is the main text.
    title = tr("hard_link_impossible", "Hard link impossible")
    box = QMessageBox(
        QMessageBox.Icon.Warning, title, title, QMessageBox.StandardButton.Ok, parent
    )
    box.setInformativeText(
        tr(
            "hard_link_impossible_text",
            "S.O.K cannot make hard links from “{0}” to “{1}”: both must be on the "
            "same drive, on a disk that supports hard links. Choose a destination "
            "on that drive, or the Move or Copy file mode in the settings.",
        ).format(folder.name or folder, Path(dest).name or dest)
    )
    box.setToolTip(f"{folder}\n→ {dest}")
    message_box.as_sheet(box, parent)
    box.exec()
    return True
