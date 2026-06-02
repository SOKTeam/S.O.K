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
"""Dedicated page for batch-renaming movie files.

Unlike the Videos page (designed around one series → N episodes), this
page lets each source file map to its own TMDB movie. A table lists every
file with an editable query, a candidate dropdown, and a live preview of
the resulting filename.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
from sok.core.media_manager import get_media_manager
from sok.file_operations import VideoFileOperations
from sok.ui.components.base import ActionButton
from sok.ui.components.inputs import DropZone
from sok.ui.components.organize.movie_batch_table import (
    MovieBatchTable,
    STATUS_OK,
)
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.controllers.ui_state import set_progress
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.factories.media_factory import create_media_item
from sok.ui.i18n import tr
from sok.ui.theme import card_shadow
from sok.ui.workers import (
    MovieBatchOrganizeWorker,
    MovieBatchSearchWorker,
    SearchWorker,
)

logger = logging.getLogger(__name__)


class MoviesPage(QScrollArea):
    """Page for batch movie renaming."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the movies page."""
        super().__init__(parent)
        self._ops = VideoFileOperations()
        self._manager = get_media_manager()
        self._files: List[Path] = []
        self._search_runner = WorkerRunner(self)
        self._rescan_runner = WorkerRunner(self)
        self._organize_runner = WorkerRunner(self)

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("Page")

        self._build()

    # ------------------------------------------------------------------ UI

    def _build(self) -> None:
        content = QWidget()
        content.setObjectName("PageContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)

        self._title_lbl = QLabel(tr("movies", "Movies"))
        self._title_lbl.setObjectName("PageTitle")
        layout.addWidget(self._title_lbl)

        self._lbl_source = make_section_label("source_files", "SOURCE FILES")
        layout.addWidget(self._lbl_source)

        self._summary_lbl = QLabel("")
        self._summary_lbl.setObjectName("EmptyState")
        self._summary_lbl.setVisible(False)
        layout.addWidget(self._summary_lbl)

        self._table = MovieBatchTable(file_extensions=self._ops.supported_extensions)
        self._table.row_changed.connect(self._refresh_previews_and_action)
        self._table.row_rescan_requested.connect(self._rescan_row)
        self._table.files_added.connect(self._on_files_added)
        layout.addWidget(self._table, 1)

        self._lbl_dest = make_section_label("destination", "DESTINATION")
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

    def stop_workers(self) -> None:
        """Stop any running worker."""
        self._search_runner.stop()
        self._rescan_runner.stop()
        self._organize_runner.stop()

    def retranslateUi(self) -> None:
        """Refresh translatable labels."""
        self._title_lbl.setText(tr("movies", "Movies"))
        self._lbl_source.setText(tr("source_files", "SOURCE FILES"))
        self._lbl_dest.setText(tr("destination", "DESTINATION"))
        self._rescan_all_btn.setText(tr("rescan_all", "Re-scan all"))
        self._action_btn.setText(tr("rename_all", "Rename all"))
        self._update_summary()

    # ------------------------------------------------------------- Sources

    def _on_files_added(self, files: List[Path]) -> None:
        """Run a batch search on newly added files only."""
        new_files = [p for p in files if p.is_file()]
        if not new_files:
            return
        self._files = self._table.files()
        self._update_summary()
        self._refresh_action_state()
        self._start_batch_search(new_files)

    def _on_dest_changed(self, _paths: List[Path]) -> None:
        self._refresh_action_state()

    # ------------------------------------------------------------ Searching

    def _start_batch_search(self, files: Optional[List[Path]] = None) -> None:
        target = files if files is not None else list(self._files)
        if not target:
            return
        for f in target:
            self._table.set_row_loading(f)
        self._set_progress(True, tr("searching", "Searching..."), 0)
        self._rescan_all_btn.setEnabled(False)
        worker = MovieBatchSearchWorker(target)
        self._search_runner.run(
            worker,
            self._on_batch_search_done,
            self._on_search_error,
            self._on_search_progress,
        )

    def _on_search_progress(self, percent: int, filename: str) -> None:
        self._set_progress(True, filename, percent)

    def _on_batch_search_done(self, results: List[Dict[str, Any]]) -> None:
        self._set_progress(False)
        self._table.apply_results(results)
        self._rescan_all_btn.setEnabled(True)
        self._refresh_previews_and_action()

    def _on_search_error(self, error: str) -> None:
        self._set_progress(False)
        self._rescan_all_btn.setEnabled(bool(self._files))
        QMessageBox.warning(
            self,
            tr("error", "Error"),
            f"{tr('search_failed', 'Search failed:')} {error}",
        )

    def _rescan_all(self) -> None:
        self._files = self._table.files()
        self._start_batch_search(self._files)

    def _rescan_row(self, file: Path, query: str) -> None:
        if not query:
            return
        self._table.set_row_loading(file)
        worker = SearchWorker(query, "movie")
        self._rescan_runner.run(
            worker,
            lambda results, f=file, q=query: self._on_row_search_done(f, q, results),
            lambda err, f=file: self._on_row_search_error(f, err),
        )

    def _on_row_search_done(
        self, file: Path, query: str, results: List[Dict[str, Any]]
    ) -> None:
        self._table.apply_search_result(
            {
                "file": file,
                "query": query,
                "year": None,
                "candidates": results[:5],
            }
        )
        self._refresh_previews_and_action()

    def _on_row_search_error(self, file: Path, error: str) -> None:
        logger.warning("Row rescan failed for %s: %s", file.name, error)
        self._table.apply_search_result(
            {"file": file, "query": "", "year": None, "candidates": []}
        )

    # ------------------------------------------------------------- Preview

    def _compute_new_name(self, file: Path, candidate: Dict[str, Any]) -> str:
        if not candidate:
            return ""
        lang = get_config_manager().get("language", "en")
        movie = create_media_item(candidate, "movie", self._manager, language=lang)
        if movie is None:
            return ""
        return self._ops.generate_new_filename(movie, file.name)

    def _refresh_previews_and_action(self) -> None:
        self._table.update_new_names(self._compute_new_name)
        self._update_summary()
        self._refresh_action_state()

    def _refresh_action_state(self) -> None:
        has_ready = any(cand is not None for _, cand in self._table.get_mappings())
        has_dest = self._dest_drop.get_path() is not None
        self._action_btn.setEnabled(has_ready and has_dest)

    def _update_summary(self) -> None:
        if not self._files:
            self._summary_lbl.setVisible(False)
            self._summary_lbl.setText("")
            return
        counts = self._table.count_by_status()
        ready = counts.get(STATUS_OK, 0)
        ambiguous = counts.get("ambiguous", 0)
        missing = counts.get("missing", 0)
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
            QMessageBox.warning(
                self,
                tr("warning", "Warning"),
                tr("select_dest_warning", "Please select a destination folder."),
            )
            return

        mappings: List[Tuple[Path, Any]] = []
        lang = get_config_manager().get("language", "en")
        for file, cand in self._table.get_mappings():
            if not cand:
                continue
            movie = create_media_item(cand, "movie", self._manager, language=lang)
            if movie is None:
                continue
            mappings.append((file, movie))

        if not mappings:
            QMessageBox.information(
                self,
                tr("info", "Info"),
                tr("no_movies_ready", "No movies are ready to rename."),
            )
            return

        msg = QMessageBox(self)
        msg.setWindowTitle(tr("confirmation", "Confirmation"))
        msg.setText(
            tr("rename_confirm", "Rename {0} movie file(s)?").format(len(mappings))
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        self._action_btn.setEnabled(False)
        self._rescan_all_btn.setEnabled(False)
        self._set_progress(True, tr("organizing", "Organizing..."), 0)
        worker = MovieBatchOrganizeWorker(mappings, str(dest), self._ops)
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

        if errors:
            QMessageBox.warning(
                self,
                tr("finished_with_errors", "Finished with errors"),
                tr("success_count", "{0}/{1} successful.").format(success, total),
            )
        else:
            QMessageBox.information(
                self,
                tr("success", "Success"),
                tr("files_organized", "✓ {0} file(s) organized!").format(success),
            )

        self._files = []
        self._table.set_files([])
        self._update_summary()
        self._refresh_action_state()

    def _on_organize_error(self, error: str) -> None:
        self._set_progress(False)
        self._action_btn.setEnabled(True)
        self._rescan_all_btn.setEnabled(True)
        QMessageBox.critical(
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
