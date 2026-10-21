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
"""Undo a rename of the history and tell the user what happened."""

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtWidgets import QWidget

from sok.core.history import MISSING, OCCUPIED, UndoReport
from sok.ui import message_box
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.i18n import tr
from sok.ui.workers.history_worker import UndoWorker

# Files listed by name in the message; the others are counted.
MAX_LISTED = 10


def reason_text(reason: str) -> str:
    """Why a file was left in place, for the user."""
    if reason == MISSING:
        return tr("undo_missing", "moved or deleted since the rename")
    if reason == OCCUPIED:
        return tr("undo_occupied", "another file has its old name")
    return tr("undo_failed", "could not be moved")


def undo_summary(report: UndoReport) -> str:
    """Text of the message shown after an undo."""
    text = tr("undo_restored", "✓ {0} file(s) put back.").format(len(report.restored))
    if report.skipped:
        lines = [
            f"• {Path(move.target).name} — {reason_text(reason)}"
            for move, reason in report.skipped[:MAX_LISTED]
        ]
        if len(report.skipped) > MAX_LISTED:
            lines.append("…")
        text += "\n\n" + tr("undo_skipped", "{0} file(s) left in place:").format(
            len(report.skipped)
        )
        text += "\n" + "\n".join(lines)
    return text


def undo_operation(
    parent: QWidget,
    runner: WorkerRunner,
    operation_id: str,
    index: Optional[int] = None,
    on_done: Optional[Callable[[UndoReport], None]] = None,
) -> None:
    """Undo an operation (or one of its files) and show the result.

    Args:
        parent: Widget the message belongs to.
        runner: Runner of the background worker.
        operation_id: The operation.
        index: One file of it, or None for all.
        on_done: Called with the report, after the message.
    """

    def finished(report: UndoReport) -> None:
        show = message_box.warning if report.skipped else message_box.information
        show(parent, tr("undo_done", "Rename undone"), undo_summary(report))
        if on_done:
            on_done(report)

    def failed(error: str) -> None:
        message_box.critical(
            parent, tr("error", "Error"), f"{tr('error_prefix', 'Error:')} {error}"
        )

    runner.run(UndoWorker(operation_id, index), finished, failed)
