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
"""Music page: albums one at a time, or tracks in batches."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from sok.ui.i18n import tr
from sok.ui.pages.organize_page import OrganizePage
from sok.ui.pages.tracks_page import TracksPage


class MusicPage(QWidget):
    """Holds the Albums page and the Tracks page, with a switch between them.

    The two pages keep their own content; their titles are hidden and this
    page shows one title with the switch next to it.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the music page."""
        super().__init__(parent)
        self.setObjectName("Page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("PageContent")
        row = QHBoxLayout(header)
        row.setContentsMargins(24, 20, 24, 0)
        self._title = QLabel()
        self._title.setObjectName("PageTitle")
        row.addWidget(self._title)
        row.addStretch()

        self._albums_btn = self._switch_button(0)
        self._tracks_btn = self._switch_button(1)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for btn in (self._albums_btn, self._tracks_btn):
            group.addButton(btn)
            row.addWidget(btn)
        layout.addWidget(header)

        self.albums = OrganizePage("music")
        self.tracks = TracksPage()
        self.albums.lbl_page_title.hide()
        self.tracks._title_lbl.hide()
        self._stack = QStackedWidget()
        self._stack.addWidget(self.albums)
        self._stack.addWidget(self.tracks)
        layout.addWidget(self._stack, 1)
        self._albums_btn.setChecked(True)
        self.retranslateUi()

    def _switch_button(self, index: int) -> QPushButton:
        btn = QPushButton()
        btn.setCheckable(True)
        btn.setObjectName("SmallBtn")
        btn.setFixedHeight(26)
        btn.setStyleSheet("padding: 0 14px;")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.toggled.connect(lambda on: self._update_switch(index, on))
        return btn

    def _update_switch(self, index: int, on: bool) -> None:
        if on:
            self._stack.setCurrentIndex(index)
        for btn in (self._albums_btn, self._tracks_btn):
            # The selected side has the accent color, the other one is plain.
            btn.setStyleSheet(
                "padding: 0 14px;"
                if btn.isChecked()
                else "padding: 0 14px; background: transparent; color: palette(text);"
            )

    def show_tracks(self) -> None:
        """Switch to the Tracks page."""
        self._tracks_btn.setChecked(True)

    def current(self) -> QWidget:
        """The page shown: albums or tracks."""
        return self._stack.currentWidget()

    def focus_search(self) -> None:
        """Focus the search of the Albums page (Find in the macOS menu)."""
        if self.current() is self.albums:
            self.albums.focus_search()

    def retranslateUi(self) -> None:
        """Refresh the texts of both pages."""
        self._title.setText(tr("music", "Music"))
        self._albums_btn.setText(tr("albums", "Albums"))
        self._tracks_btn.setText(tr("tracks", "Tracks"))
        self.albums.retranslateUi()
        self.tracks.retranslateUi()

    def stop_workers(self) -> None:
        """Stop the workers of both pages."""
        self.albums.stop_workers()
        self.tracks.stop_workers()
