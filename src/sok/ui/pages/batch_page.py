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
"""Base page for batch renaming: movies, books…

Unlike the TV shows page (designed around one series → N episodes), a
batch page lets each item map to its own online match. A table lists every
item with an editable query, a candidate dropdown, a status and a live
preview of the resulting filename. Subclasses say what they search and how
they name the files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sok.config import get_config_manager
from sok.core.batch import (
    STATUS_AMBIGUOUS,
    STATUS_MISSING,
    BatchMatch,
    QueryParser,
    SameWork,
)
from sok.core.interfaces import ContentType, MediaType
from sok.core.media_manager import get_media_manager
from sok.ui.components.base import ActionButton
from sok.ui.components.inputs import DropZone
from sok.ui.components.organize.media_batch_table import (
    Describe,
    GroupFiles,
    MediaBatchTable,
    STATUS_OK,
    describe_dated,
    one_item_per_file,
)
from sok.ui.controllers.default_paths import apply_default_destination
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.controllers.ui_state import set_progress
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.factories.media_factory import create_media_item
from sok.ui.i18n import tr
from sok.ui.theme import card_shadow
from sok.ui.workers import (
    BatchOrganizeWorker,
    BatchSearchWorker,
)
from sok.ui import message_box
from sok.ui.platform import request_attention

logger = logging.getLogger(__name__)


class BatchPage(QScrollArea):
    """Page for batch renaming, configured by its subclasses.

    Subclasses set the class attributes and implement make_ops(),
    organize_method() and the text methods.

    Attributes:
        default_path_type: Media type of the default destination folder
            ("video", "book"…).
        media_type: Media type whose selected API is searched.
        content_type: What to search.
        factory_type: Content type given to create_media_item().
        parse: Reads the file name of an item.
        same_work: Tells when several results are one work.
        localized: Ask for results in the language of the app.
        describe: Text of a candidate in the menu of a row.
        group_files: Splits added files into items.
    """

    default_path_type = "video"
    media_type = MediaType.VIDEO
    content_type = ContentType.MOVIE
    factory_type = "movie"
    parse: QueryParser
    same_work: Optional[SameWork] = None
    localized = True
    describe: Describe = staticmethod(describe_dated)
    group_files: GroupFiles = staticmethod(one_item_per_file)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the page."""
        super().__init__(parent)
        self._ops = self.make_ops()
        self._manager = get_media_manager()
        self._files: List[Path] = []
        self._search_runner = WorkerRunner(self)
        self._rescan_runner = WorkerRunner(self)
        self._organize_runner = WorkerRunner(self)

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("Page")

        self._build()
        apply_default_destination(self._dest_drop, self.default_path_type)

    # ------------------------------------------------------- Subclass hooks

    def make_ops(self) -> Any:
        """Return the file operations of the media type."""
        raise NotImplementedError

    def organize_method(self) -> Callable[..., Dict[str, Any]]:
        """Return the method of the file operations that moves the files."""
        raise NotImplementedError

    def page_title(self) -> str:
        """Title of the page."""
        raise NotImplementedError

    def empty_hint(self) -> str:
        """Text of the empty table."""
        raise NotImplementedError

    def add_more_text(self) -> str:
        """Text of the button under the rows."""
        raise NotImplementedError

    def query_placeholder(self) -> str:
        """Hint shown in an empty query field."""
        return ""

    def preview_name(self, item: Any, file: Path) -> str:
        """New name shown in a row for its first file."""
        return self._ops.generate_new_filename(item, file.name)

    def rename_confirm_text(self, count: int) -> str:
        """Question asked before renaming count files."""
        return tr("rename_confirm_files", "Rename {0} file(s)?").format(count)

    def nothing_ready_text(self) -> str:
        """Message when no row is ready."""
        return tr("nothing_ready", "No file is ready to rename.")

    # ------------------------------------------------------------------ UI

    def _build(self) -> None:
        content = QWidget()
        content.setObjectName("PageContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        self._title_lbl = QLabel(self.page_title())
        self._title_lbl.setObjectName("PageTitle")
        layout.addWidget(self._title_lbl)

        self._lbl_source = make_section_label("source_files", "Source Files")
        layout.addWidget(self._lbl_source)

        self._summary_lbl = QLabel("")
        self._summary_lbl.setObjectName("EmptyState")
        self._summary_lbl.setVisible(False)
        layout.addWidget(self._summary_lbl)

        self._table = MediaBatchTable(
            file_extensions=self._ops.supported_extensions,
            empty_hint=self.empty_hint(),
            add_more_text=self.add_more_text(),
            describe=self.describe,
            query_placeholder=self.query_placeholder(),
            group_files=self.group_files,
        )
        self._table.row_changed.connect(self._refresh_previews_and_action)
        self._table.row_rescan_requested.connect(self._rescan_row)
        self._table.files_added.connect(self._on_files_added)
        layout.addWidget(self._table, 1)

        self._lbl_dest = make_section_label("destination", "Destination")
        layout.addWidget(self._lbl_dest)
        self._dest_drop = DropZone()
        self._dest_drop.files_dropped.connect(self._on_dest_changed)
        self._dest_drop.setGraphicsEffect(card_shadow())
        layout.addWidget(self._dest_drop)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(6)
        self._progress.setVisible(False)
        self._progress.setTextVisible(False)
        self._progress.setObjectName("Progress")
        layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("EmptyState")
        self._progress_label.setVisible(False)
        layout.addWidget(self._progress_label)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        action_row.addStretch()

        self._rescan_all_btn = ActionButton(tr("rescan_all", "Re-scan all"))
        self._rescan_all_btn.setEnabled(False)
        self._rescan_all_btn.clicked.connect(self._rescan_all)
        action_row.addWidget(self._rescan_all_btn)

        self._action_btn = ActionButton(tr("rename_all", "Rename all"))
        self._action_btn.setEnabled(False)
        self._action_btn.clicked.connect(self._start_rename)
        action_row.addWidget(self._action_btn)

        layout.addLayout(action_row)

        self.setWidget(content)
        self.retranslateUi()

    # ----------------------------------------------------------------- I/O

    def showEvent(self, event) -> None:
        """Apply the default destination set in the settings since startup."""
        apply_default_destination(self._dest_drop, self.default_path_type)
        super().showEvent(event)

    def stop_workers(self) -> None:
        """Stop any running worker."""
        self._search_runner.stop()
        self._rescan_runner.stop()
        self._organize_runner.stop()

    def retranslateUi(self) -> None:
        """Refresh translatable labels."""
        self._title_lbl.setText(self.page_title())
        self._lbl_source.setText(tr("source_files", "Source Files"))
        self._lbl_dest.setText(tr("destination", "Destination"))
        self._rescan_all_btn.setText(tr("rescan_all", "Re-scan all"))
        self._action_btn.setText(tr("rename_all", "Rename all"))
        self._table.set_texts(self.empty_hint(), self.add_more_text())
        self._update_summary()

    # ------------------------------------------------------------- Sources

    def load_files(self, files: List[Path]) -> None:
        """Add files found elsewhere, such as on the home page, and search them.

        Args:
            files: Files to add; those already in the table are skipped.
        """
        self._on_files_added(self._table.add_files(files))

    def _on_files_added(self, items: List[List[Path]]) -> None:
        """Run a batch search on newly added items only."""
        if not items:
            return
        self._files = self._table.files()
        self._update_summary()
        self._refresh_action_state()
        self._start_batch_search(items)

    def _on_dest_changed(self, _paths: List[Path]) -> None:
        self._refresh_action_state()

    # ------------------------------------------------------------ Searching

    def _start_batch_search(self, items: Optional[List[List[Path]]] = None) -> None:
        target = items if items is not None else self._table.items()
        if not target:
            return
        for item in target:
            self._table.set_row_loading(item[0])
        self._set_progress(True, tr("searching", "Searching..."), 0)
        self._rescan_all_btn.setEnabled(False)
        worker = BatchSearchWorker(
            target,
            self.media_type,
            self.content_type,
            self.parse,
            same_work=self.same_work,
            localized=self.localized,
        )
        self._search_runner.run(
            worker,
            self._on_batch_search_done,
            self._on_search_error,
            self._on_search_progress,
        )

    def _on_search_progress(self, percent: int, filename: str) -> None:
        self._set_progress(True, filename, percent)

    def _on_batch_search_done(self, results: List[BatchMatch]) -> None:
        self._set_progress(False)
        self._table.apply_results(results)
        self._rescan_all_btn.setEnabled(True)
        self._refresh_previews_and_action()

    def _on_search_error(self, error: str) -> None:
        self._set_progress(False)
        self._table.fail_pending()
        self._update_summary()
        self._rescan_all_btn.setEnabled(bool(self._files))
        message_box.warning(
            self,
            tr("error", "Error"),
            f"{tr('search_failed', 'Search failed:')} {error}",
        )

    def _rescan_all(self) -> None:
        self._files = self._table.files()
        self._start_batch_search()

    def _rescan_row(self, key: Path, query: str) -> None:
        files = self._table.item_files(key)
        if not query or not files:
            return
        self._table.set_row_loading(key)
        worker = BatchSearchWorker(
            [files],
            self.media_type,
            self.content_type,
            self.parse,
            query,
            same_work=self.same_work,
            localized=self.localized,
        )
        self._rescan_runner.run(
            worker,
            self._on_row_search_done,
            lambda err, f=files, q=query: self._on_row_search_error(f, q, err),
        )

    def _on_row_search_done(self, results: List[BatchMatch]) -> None:
        for result in results:
            self._table.apply_search_result(result)
        self._refresh_previews_and_action()

    def _on_row_search_error(self, files: List[Path], query: str, error: str) -> None:
        logger.warning("Row rescan failed for %s: %s", files[0].name, error)
        self._table.apply_search_result(BatchMatch(files, query, None))
        self._refresh_previews_and_action()
        message_box.warning(
            self,
            tr("error", "Error"),
            f"{tr('search_failed', 'Search failed:')} {error}",
        )

    # ------------------------------------------------------------- Preview

    def _compute_new_name(self, files: List[Path], candidate: Dict[str, Any]) -> str:
        if not candidate:
            return ""
        file = files[0]
        lang = get_config_manager().get("language", "en")
        item = create_media_item(
            candidate, self.factory_type, self._manager, language=lang
        )
        if item is None:
            return ""
        return self.preview_name(item, file)

    def _refresh_previews_and_action(self) -> None:
        self._table.update_new_names(self._compute_new_name)
        self._update_summary()
        self._refresh_action_state()

    def _refresh_action_state(self) -> None:
        has_ready = bool(self._table.get_ready_mappings())
        has_dest = self._dest_drop.get_path() is not None
        self._action_btn.setEnabled(has_ready and has_dest)

    def _update_summary(self) -> None:
        if not self._files:
            self._summary_lbl.setVisible(False)
            self._summary_lbl.setText("")
            return
        counts = self._table.count_by_status()
        ready = counts.get(STATUS_OK, 0)
        ambiguous = counts.get(STATUS_AMBIGUOUS, 0)
        missing = counts.get(STATUS_MISSING, 0)
        pending = counts.get("pending", 0)
        parts = [
            f"{len(self._files)} {tr('files_count', 'file(s)')}",
            f"✓ {ready}",
            f"⚠ {ambiguous}",
            f"✗ {missing}",
        ]
        if pending:
            parts.append(f"… {pending}")
        self._summary_lbl.setText(" · ".join(parts))
        self._summary_lbl.setVisible(True)

    # -------------------------------------------------------------- Rename

    def _start_rename(self) -> None:
        dest = self._dest_drop.get_path()
        if not dest or not Path(dest).exists():
            message_box.warning(
                self,
                tr("warning", "Warning"),
                tr("select_dest_warning", "Please select a destination folder."),
            )
            return

        mappings: List[Tuple[Path, Any]] = []
        lang = get_config_manager().get("language", "en")
        for files, cand in self._table.get_ready_mappings():
            item = create_media_item(
                cand, self.factory_type, self._manager, language=lang
            )
            if item is None:
                continue
            mappings.extend((file, item) for file in files)

        if not mappings:
            message_box.information(
                self,
                tr("info", "Info"),
                self.nothing_ready_text(),
            )
            return

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("confirmation", "Confirmation"))
        msg.setText(self.rename_confirm_text(len(mappings)))
        to_pick = self._table.count_by_status().get(STATUS_AMBIGUOUS, 0)
        if to_pick:
            msg.setInformativeText(
                tr(
                    "rename_skips_to_pick",
                    "{0} file(s) still to pick will be left as they are.",
                ).format(to_pick)
            )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        message_box.as_sheet(msg, self)
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        self._action_btn.setEnabled(False)
        self._rescan_all_btn.setEnabled(False)
        self._set_progress(True, tr("organizing", "Organizing..."), 0)
        worker = BatchOrganizeWorker(mappings, str(dest), self.organize_method())
        self._organize_runner.run(
            worker,
            self._on_organize_done,
            self._on_organize_error,
            self._on_search_progress,
        )

    def _on_organize_done(self, report: Dict[str, Any]) -> None:
        self._set_progress(False)
        self._rescan_all_btn.setEnabled(True)
        success = report.get("success", 0)
        total = report.get("total", 0)
        errors = report.get("errors", [])
        dest = self._dest_drop.get_path()
        reveal = Path(dest) if dest and Path(dest).is_dir() else None
        request_attention(self)

        if errors:
            message_box.warning(
                self,
                tr("finished_with_errors", "Finished with errors"),
                tr("success_count", "{0}/{1} successful.").format(success, total),
                reveal=reveal,
            )
        else:
            message_box.information(
                self,
                tr("success", "Success"),
                tr("files_organized", "✓ {0} file(s) organized!").format(success),
                reveal=reveal,
            )

        # Rows still to pick stay, so the user can finish them.
        self._table.remove_files([Path(m["from"]) for m in report.get("moved", [])])
        self._files = self._table.files()
        self._update_summary()
        self._refresh_action_state()

    def _on_organize_error(self, error: str) -> None:
        self._set_progress(False)
        request_attention(self)
        self._action_btn.setEnabled(True)
        self._rescan_all_btn.setEnabled(True)
        message_box.critical(
            self,
            tr("error", "Error"),
            f"{tr('error_prefix', 'Error:')} {error}",
        )

    # -------------------------------------------------------------- Helpers

    def _set_progress(
        self,
        visible: bool,
        message: Optional[str] = None,
        value: Optional[int] = None,
    ) -> None:
        set_progress(self._progress, self._progress_label, visible, message, value)

    def closeEvent(self, event):
        """Stop background workers on close."""
        self.stop_workers()
        super().closeEvent(event)
