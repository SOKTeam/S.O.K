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
Organize Page
"""

import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QScrollArea,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from sok.file_operations import (
    VideoFileOperations,
    MusicFileOperations,
    BookFileOperations,
    GameFileOperations,
)
from sok.ui.components.organize import SearchPanel, OptionsPanel
from sok.ui.controllers.organize_preview import OrganizePreviewController
from sok.ui.controllers.source_scanner import scan_sources
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.workers import (
    SearchWorker,
    OrganizeWorker,
    DetailsWorker,
    CreateFoldersWorker,
)
from sok.ui.factories.media_factory import create_media_item
from sok.core.media_manager import get_media_manager
from sok.config import get_config_manager
from sok.ui.i18n import tr
from sok.ui.pages.organize_preview_panel import PreviewPanel
from sok.media.video.series import Series

FileOperations = (
    VideoFileOperations | MusicFileOperations | BookFileOperations | GameFileOperations
)

logger = logging.getLogger(__name__)

MAX_PREVIEW_FILES = 15


class OrganizePage(QScrollArea):
    """Media organization page.

    Provides UI for searching media, selecting files, and organizing
    them with proper naming and folder structure.

    Attributes:
        _type: Media type (video, music, book, game).
        _ops: File operations handler for the media type.
        _manager: Universal media manager instance.
        _files: List of files to organize.
    """

    def __init__(self, media_type: str, parent=None):
        """Initialize the organize page.

        Args:
            media_type: Type of media (video, music, book, game).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._type = media_type
        self._ops: FileOperations

        if media_type == "video":
            self._ops = VideoFileOperations()
        elif media_type == "music":
            self._ops = MusicFileOperations()
        elif media_type == "book":
            self._ops = BookFileOperations()
        elif media_type == "game":
            self._ops = GameFileOperations()
        else:
            self._ops = VideoFileOperations()

        self._manager = get_media_manager()
        self._translations = get_config_manager().load_language()
        self._files: list[Path] = []
        self._preview_controller = OrganizePreviewController(
            self._ops, tr, MAX_PREVIEW_FILES
        )
        self._worker_runner = WorkerRunner(self)

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("Page")

        self._build()

    def showEvent(self, event):
        """Handle page show event.

        Updates preview and actions when page becomes visible.

        Args:
            event: Show event.
        """
        super().showEvent(event)
        self._update_preview_and_actions()

    def closeEvent(self, event):
        """Handle page close event.

        Stops background workers before closing.

        Args:
            event: Close event.
        """
        self.stop_workers()
        super().closeEvent(event)

    def _build(self):
        """Build the organize page layout.

        Creates search panel, options panel, and preview panel.
        """
        content = QWidget()
        content.setObjectName("PageContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(20)

        self.lbl_page_title = QLabel()
        self.lbl_page_title.setObjectName("PageTitle")
        layout.addWidget(self.lbl_page_title)

        main_h = QHBoxLayout()
        main_h.setSpacing(20)

        left = QVBoxLayout()
        left.setSpacing(16)

        self._search_panel = SearchPanel(self._type)
        self._search_panel.search_started.connect(self._do_search)
        self._search_panel.media_selected.connect(self._on_media_selected)
        self._search_panel.type_changed.connect(self._on_type_changed)
        left.addWidget(self._search_panel)

        self._options_panel = OptionsPanel(self._type)
        self._options_panel.source_changed.connect(self._on_source)
        self._options_panel.destination_changed.connect(self._on_dest_dropped)
        self._options_panel.organize_clicked.connect(self._start_organize)
        self._options_panel.create_folders_clicked.connect(self._create_series_folders)
        left.addWidget(self._options_panel)

        left.addStretch()

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        main_h.addWidget(left_widget, 1)

        right_widget = QWidget()
        right_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        right = QVBoxLayout(right_widget)
        right.setSpacing(8)

        self._preview_title_label = make_section_label("preview", "PREVIEW")
        right.addWidget(self._preview_title_label)

        self._preview_panel = PreviewPanel()
        right.addWidget(self._preview_panel)
        right.addStretch()

        main_h.addWidget(right_widget, 1)

        layout.addLayout(main_h)
        self.setWidget(content)
        self.retranslateUi()

    def _set_progress(
        self, visible: bool, message: str | None = None, value: int | None = None
    ):
        """Set progress bar visibility and state.

        Args:
            visible: Whether to show the progress bar.
            message: Optional status message.
            value: Optional progress percentage (0-100).
        """
        self._options_panel.set_progress(visible, message, value)

    def _set_empty_preview(self, text: str, height: int = 200):
        """Display empty state in preview panel.

        Args:
            text: Message to display.
            height: Minimum height for the empty state.
        """
        self._preview_panel.set_empty(text, height)

    def _populate_preview_rows(self):
        """Build and render preview rows from found files.

        Creates preview rows for files up to MAX_PREVIEW_FILES limit.
        """
        rows, more_label = self._preview_controller.build_preview(self._files)
        self._preview_panel.render_preview(rows, more_label)

    def retranslateUi(self):
        """Update all translatable text in the organize page.

        Called after language changes to refresh UI strings.
        """
        self._translations = get_config_manager().load_language()

        titles = {
            "video": tr("videos", "Videos"),
            "music": tr("music", "Music"),
            "book": tr("books", "Books"),
            "game": tr("games", "Games"),
        }
        self.lbl_page_title.setText(titles.get(self._type, tr("files", "Files")))

        self._search_panel.retranslate_ui()
        self._options_panel.retranslate_ui()

        if not self._files:
            self._set_empty_preview(tr("select_folder", "Select a folder"))
            self._preview_title_label.setText(tr("preview", "PREVIEW"))
        else:
            self._on_source([f.parent for f in self._files])

    def _reset_search_and_selection(self):
        """Reset search panel and selected media.

        Clears the current search query and media selection.
        """
        self._search_panel.reset()

    def stop_workers(self):
        """Stop all running background workers.

        Ensures proper cleanup of worker threads.
        """
        self._worker_runner.stop()

    def _run_worker(self, worker, on_finished, on_error, on_progress=None):
        """Run a worker in a dedicated thread.

        Args:
            worker: Worker object to run.
            on_finished: Callback for completion.
            on_error: Callback for errors.
            on_progress: Optional progress callback.

        Returns:
            Worker runner result.
        """
        return self._worker_runner.run(worker, on_finished, on_error, on_progress)

    def _on_type_changed(self, content_type: str):
        """Handle content type change in SearchPanel.

        Args:
            content_type: New content type string.
        """
        pass

    def _do_search(self, query: str):
        """Execute search via the media manager.

        Args:
            query: Search query string.
        """
        if not query:
            return

        content_type = self._search_panel.get_content_type()
        worker = SearchWorker(query, content_type)
        self._run_worker(worker, self._on_search_results, self._on_search_error)

    def _on_search_results(self, results: list):
        """Handle search completion.

        Args:
            results: List of search results.
        """
        self._search_panel.display_results(results)

    def _on_search_error(self, error: str):
        """Handle search error.

        Args:
            error: Error message string.
        """
        self._search_panel.display_error(error)

    def _on_media_selected(self, data: dict, content_type: str):
        """Handle media selection in SearchPanel.

        Args:
            data: Selected media data dictionary.
            content_type: Content type of selected media.
        """
        self._options_panel.update_create_folders_visibility(
            content_type, data is not None
        )

        if content_type == "tv" and data:
            self._search_panel.set_status(tr("loading_episodes", "Loading episodes..."))
            worker = DetailsWorker(str(data["id"]), "tv", fetch_episodes=True)
            self._run_worker(
                worker, self._on_preview_details_received, self._on_details_error
            )

        self._update_preview_and_actions()

    def _on_preview_details_received(self, details: dict):
        """Handle details fetch completion for preview.

        Updates selected media with episode information.

        Args:
            details: Media details dictionary with episodes.
        """
        self._search_panel.set_status("")
        selected_media = self._search_panel.get_selected_media()
        if selected_media and str(selected_media.get("id")) == str(details.get("id")):
            self._search_panel.update_selected_media(details)
            self._update_preview_and_actions()

    def _on_source(self, paths):
        """Handle source folder selection.

        Scans selected folders for media files and updates preview.

        Args:
            paths: List of source folder paths.
        """
        if not paths:
            self._files = []
            self._preview_title_label.setText(tr("preview_title", "Preview"))

            self._set_empty_preview(tr("select_folder", "Select a folder"))
            self._reset_search_and_selection()

            self._update_preview_and_actions()
            return

        self._preview_panel.clear()
        self._files = scan_sources(self._ops, paths)

        sources_text = (
            f"{len(paths)} {tr('folders_count', 'folder(s)')}"
            if len(paths) > 1
            else paths[0].name
        )
        self._preview_title_label.setText(
            f"{tr('preview_title', 'Preview')} ({len(self._files)} {tr('files_from', 'files from')} {sources_text})"
        )

        if not self._files:
            self._set_empty_preview(tr("no_files_found", "No files found"), height=40)
        else:
            first_file_name = self._files[0].name
            (
                detected_query,
                detected_type,
            ) = self._preview_controller.detect_query_and_type(
                first_file_name, self._type
            )

            if detected_type == "series":
                self._search_panel.set_type_by_data("tv")
            elif detected_type == "movie":
                self._search_panel.set_type_by_data("movie")
            elif detected_type == "album":
                self._search_panel.set_type_by_data("album")
            elif detected_type == "artist":
                self._search_panel.set_type_by_data("artist")

            if detected_query:
                self._search_panel.set_search_text(detected_query, auto_select=True)

            self._populate_preview_rows()

        self._update_preview_and_actions()

    def _on_dest_dropped(self, dest_path: str):
        """Handle destination folder selection.

        Args:
            dest_path: Selected destination folder path.
        """
        self._update_preview_and_actions()

    def _update_preview_and_actions(self):
        """Update preview names and action button state.

        Groups related interface updates for efficiency.
        """
        self._update_preview_names()
        self._update_action_btn()

    def _compute_new_name(
        self, file: Path, media_info: dict | None, content_type: str
    ) -> str:
        """Compute new filename for a media file.

        Uses MediaItem factory and FileOperations to generate proper name.

        Args:
            file: Original file path.
            media_info: Selected media information dictionary.
            content_type: Content type string.

        Returns:
            Generated new filename, or empty string if unavailable.
        """
        if not media_info:
            return ""
        lang = get_config_manager().get("language", "en")
        media_item = create_media_item(
            media_info, content_type, self._manager, language=lang
        )
        if media_item and hasattr(self._ops, "generate_new_filename"):
            return self._ops.generate_new_filename(media_item, file.name)
        return ""

    def _update_preview_names(self):
        """Update computed new names in preview panel.

        Recalculates names based on current media selection.
        """
        selected_media = self._search_panel.get_selected_media()
        content_type = self._search_panel.get_content_type()
        self._preview_panel.update_new_names(
            lambda file: self._compute_new_name(file, selected_media, content_type)  # type: ignore[arg-type]
        )

    def _update_action_btn(self):
        """Update action button state in OptionsPanel.

        Enables or disables based on file and media selection.
        """
        has_files = len(self._files) > 0
        selected_media = self._search_panel.get_selected_media()
        has_media = selected_media is not None
        content_type = self._search_panel.get_content_type()

        self._options_panel.update_action_state(has_files, has_media)
        self._options_panel.update_create_folders_visibility(content_type, has_media)

    def _create_series_folders(self):
        """Create folder structure for TV series.

        Retrieves season count from API and creates season folders
        in the destination directory.
        """
        selected_media = self._search_panel.get_selected_media()
        content_type = self._search_panel.get_content_type()

        if not selected_media or content_type != "tv":
            return
        dest = self._options_panel.get_destination_path()
        if not dest or not Path(dest).exists():
            QMessageBox.warning(
                self,
                tr("warning", "Warning"),
                tr("select_dest_warning", "Please select a destination folder."),
            )
            return

        series_id = selected_media.get("id")
        if not series_id:
            QMessageBox.warning(
                self,
                tr("error", "Error"),
                tr("series_id_not_found", "Series ID not found."),
            )
            return

        self._options_panel.set_create_folders_enabled(False)
        self._options_panel.set_create_folders_text(tr("loading", "Loading..."))

        worker = DetailsWorker(str(series_id), "tv")
        self._run_worker(worker, self._on_details_received, self._on_details_error)

    def _on_details_received(self, details: dict):
        """Handle received series details from API.

        Creates season folder structure in the destination directory.

        Args:
            details: Series details dictionary containing season information.
        """
        dest = self._options_panel.get_destination_path()
        selected_media = self._search_panel.get_selected_media()
        title = details.get(
            "name",
            selected_media.get("name", "Unknown") if selected_media else "Unknown",
        )
        num_seasons = details.get("number_of_seasons", 0)

        if not num_seasons or num_seasons < 1:
            self._options_panel.set_create_folders_enabled(True)
            self._options_panel.set_create_folders_text(
                tr("create_series_folders", "Create series folders")
            )
            QMessageBox.warning(
                self,
                tr("warning", "Warning"),
                tr("no_seasons_found", "No seasons found for '{title}'.").format(
                    title=title
                ),
            )
            return

        try:
            self._search_panel.update_selected_media(details)

            season_word = tr("season", "Season")
            seasons_data = details.get("seasons", [])
            seasons = {}

            for i in range(1, num_seasons + 1):
                season_name = None
                for s in seasons_data:
                    if s.get("season_number") == i:
                        season_name = s.get("name", "")
                        break

                if season_name and season_name.lower() not in [
                    f"season {i}",
                    f"saison {i}",
                    "",
                ]:
                    folder_name = f"{season_word} {i} - {season_name}"
                else:
                    folder_name = f"{season_word} {i}"

                seasons[folder_name] = i

            self._set_progress(True, tr("creating_folders", "Creating folders..."), 0)

            worker = CreateFoldersWorker(str(dest), title, seasons)
            self._run_worker(
                worker,
                self._on_folders_created,
                self._on_folders_error,
                self._on_progress,
            )

        except (OSError, ValueError, KeyError) as e:
            logger.exception("Folder creation flow failed", exc_info=e)
            self._options_panel.set_create_folders_enabled(True)
            self._options_panel.set_create_folders_text(
                tr("create_series_folders", "Create series folders")
            )
            QMessageBox.critical(
                self,
                tr("error", "Error"),
                tr("creation_error", "Error during creation: {e}").format(e=e),
            )

    def _on_folders_created(self, report: dict):
        """Handle completed folder creation operation.

        Shows success or error message based on creation results.

        Args:
            report: Report dictionary with 'created' count and 'errors' list.
        """
        self._set_progress(False)
        self._options_panel.set_create_folders_enabled(True)
        self._options_panel.set_create_folders_text(
            tr("create_series_folders", "Create series folders")
        )

        selected_media = self._search_panel.get_selected_media()
        title = selected_media.get("name", "Unknown") if selected_media else "Unknown"
        num_created = report.get("created", 0)
        errors = report.get("errors", [])

        if errors:
            QMessageBox.warning(
                self,
                tr("finished_with_errors", "Finished with errors"),
                f"Structure created for '{title}':\n{num_created} folder(s) created\n{len(errors)} error(s)",
            )
        else:
            QMessageBox.information(
                self,
                tr("success", "Success"),
                f"Structure created for '{title}':\n{num_created} folder(s) created",
            )

    def _on_folders_error(self, error: str):
        """Handle folder creation error.

        Resets UI state and displays error message to user.

        Args:
            error: Error message string describing the failure.
        """
        self._set_progress(False)
        self._options_panel.set_create_folders_enabled(True)
        self._options_panel.set_create_folders_text(
            tr("create_series_folders", "Create series folders")
        )
        QMessageBox.critical(
            self,
            tr("error", "Error"),
            tr("creation_error", "Error during creation:\n{error}").format(error=error),
        )

    def _on_details_error(self, error: str):
        """Handle series details retrieval error.

        Resets button state and shows error dialog.

        Args:
            error: Error message string from the API call.
        """
        self._options_panel.set_create_folders_enabled(True)
        self._options_panel.set_create_folders_text(
            tr("create_series_folders", "Create series folders")
        )
        QMessageBox.critical(
            self,
            tr("error", "Error"),
            tr("details_error", "Unable to retrieve details:\n{error}").format(
                error=error
            ),
        )

    def _start_organize(self):
        """Start the file organization process.

        Validates destination and media selection, shows confirmation dialog,
        then initiates the organization worker. For TV content, fetches
        episode details first.
        """
        dest_path = self._options_panel.get_destination_path()
        if not self._files or not dest_path or not Path(dest_path).exists():
            return

        selected_media = self._search_panel.get_selected_media()
        content_type = self._search_panel.get_content_type()

        if self._type == "video" and not selected_media:
            QMessageBox.warning(
                self,
                tr("warning", "Warning"),
                tr("select_media_warning", "Please select a media."),
            )
            return

        msg = QMessageBox()
        msg.setWindowTitle(tr("confirmation", "Confirmation"))
        msg.setText(
            tr("organize_confirm", "Organize {0} file(s)?").format(len(self._files))
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        self._options_panel.set_action_enabled(False)
        self._set_progress(True, tr("fetching_info", "Fetching information..."), 0)

        if content_type == "tv" and selected_media:
            series_id = selected_media.get("id")
            if series_id:
                worker = DetailsWorker(str(series_id), "tv", fetch_episodes=True)
                self._run_worker(
                    worker, self._on_episodes_received, self._on_organize_error
                )
                return

        self._do_organize()

    def _on_episodes_received(self, details: dict):
        """Handle received episode details for TV series.

        Updates selected media with episode information and proceeds
        to organize files.

        Args:
            details: Series details dictionary including episodes data.
        """
        self._search_panel.update_selected_media(details)
        self._do_organize()

    def _do_organize(self):
        """Execute the actual file organization operation.

        Creates media item from selection, configures season/episode data
        for TV content, and starts the organize worker.
        """
        self._set_progress(True, tr("organizing", "Organizing..."))

        selected_media = self._search_panel.get_selected_media()
        content_type = self._search_panel.get_content_type()

        lang = get_config_manager().get("language", "en")
        media_item = create_media_item(
            selected_media or {}, content_type, self._manager, language=lang
        )

        if content_type == "tv" and media_item and selected_media:
            if isinstance(media_item, Series):
                num_seasons = selected_media.get("number_of_seasons", 0)
                if num_seasons:
                    season_word = tr("season", "Season")
                    seasons_data = selected_media.get("seasons", [])
                    media_item.seasons = {}

                    for i in range(1, num_seasons + 1):
                        season_name = None
                        for s in seasons_data:
                            if s.get("season_number") == i:
                                season_name = s.get("name", "")
                                break

                        i_padded = str(i)
                        if season_name and season_name.lower() not in [
                            f"season {i}",
                            f"saison {i}",
                            "",
                        ]:
                            folder_name = f"{season_word} {i_padded} - {season_name}"
                        else:
                            folder_name = f"{season_word} {i_padded}"

                        media_item.seasons[folder_name] = i

                episodes = selected_media.get("episodes", {})
                if episodes:
                    media_item.episodes = episodes

        worker = OrganizeWorker(
            self._files,
            self._options_panel.get_destination_path(),
            media_item,
            self._ops,
        )
        self._run_worker(
            worker, self._on_organize_done, self._on_organize_error, self._on_progress
        )

    def _on_progress(self, percent: int, message: str):
        """Handle progress updates from workers.

        Args:
            percent: Progress percentage (0-100).
            message: Status message to display.
        """
        self._set_progress(True, message, percent)

    def _on_organize_done(self, report: dict):
        """Handle completed organization operation.

        Shows success or error summary and resets the page state.

        Args:
            report: Report dictionary with 'success', 'total', and 'errors'.
        """
        self._set_progress(False)
        self._options_panel.set_action_enabled(True)

        if report["errors"]:
            QMessageBox.warning(
                self,
                tr("finished_with_errors", "Finished with errors"),
                tr("success_count", "{0}/{1} succeeded.").format(
                    report["success"], report["total"]
                ),
            )
        else:
            QMessageBox.information(
                self,
                tr("success", "Success"),
                tr("files_organized", "✓ {0} file(s) organized!").format(
                    report["success"]
                ),
            )

        self._files = []
        self._preview_title_label.setText(tr("preview_title", "Preview"))
        self._set_empty_preview(tr("select_folder", "Select a folder"), height=60)

    def _on_organize_error(self, error: str):
        """Handle organization error.

        Re-enables action button and shows error dialog.

        Args:
            error: Error message string describing the failure.
        """
        self._set_progress(False)
        self._options_panel.set_action_enabled(True)
        QMessageBox.critical(
            self, tr("error", "Error"), f"{tr('error_prefix', 'Error:')} {error}"
        )
