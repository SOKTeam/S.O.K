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
Home Page - Dashboard and Quick Actions
"""

import sys

import shutil
import ctypes
import string
import os
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QScrollArea,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QPixmap, QPainter, QFont

from sok.ui.theme import Theme, card_shadow, ASSETS_DIR, svg_icon
from sok.ui.components.base import Card, parse_color
from sok.ui.components.layouts import FlowLayout
from sok.config import get_config_manager
from sok.ui.i18n import tr
from sok.ui.controllers.worker_runner import WorkerRunner
from sok.ui.controllers.ui_helpers import make_section_label

logger = logging.getLogger(__name__)


class StatsWorker(QObject):
    """Background worker for drive statistics collection.

    Collects disk space information for all available drives
    using QObject + WorkerRunner pattern.

    Attributes:
        stats_ready: Signal emitted with stats dictionary.
        finished: Signal emitted when work completes.
        error: Signal emitted on error with message.
    """

    stats_ready = Signal(dict)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, video_path=None, music_path=None):
        """Initialize the stats worker.

        Args:
            video_path: Optional video folder path.
            music_path: Optional music folder path.
        """
        super().__init__()
        self.video_path = Path(video_path) if video_path else None
        self.music_path = Path(music_path) if music_path else None
        self._is_running = True

    def stop(self):
        """Stop the worker."""
        self._is_running = False

    def run(self):
        """Execute drive statistics collection."""
        try:
            drives = []

            available_drives = []
            try:
                if sys.platform == "win32":
                    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                    for letter in string.ascii_uppercase:
                        if not self._is_running:
                            return
                        if bitmask & 1:
                            available_drives.append(f"{letter}:\\")
                        bitmask >>= 1
            except OSError as exc:
                logger.warning(
                    "Drive detection failed, fallback to exists(): %s",
                    exc,
                    exc_info=exc,
                )
                for d in string.ascii_uppercase:
                    if not self._is_running:
                        return
                    if os.path.exists(f"{d}:\\"):
                        available_drives.append(f"{d}:\\")

            if not available_drives:
                available_drives.append(Path.cwd().anchor)

            for drive_path in available_drives:
                if not self._is_running:
                    return
                try:
                    total, used, free = shutil.disk_usage(drive_path)

                    if total < 1024**3:
                        continue

                    percent_free = free / total
                    label = f"{tr('drive', 'Drive')} {drive_path[0]}"

                    if free > 1024**4:
                        free_str = f"{free / (1024**4):.2f} {tr('tb_free', 'TB Free')}"
                    elif free > 1024**3:
                        free_str = f"{free / (1024**3):.0f} {tr('gb_free', 'GB Free')}"
                    else:
                        free_str = f"{free / (1024**2):.0f} {tr('mb_free', 'MB Free')}"

                    drives.append(
                        {
                            "label": label,
                            "free_str": free_str,
                            "percent_free": percent_free,
                        }
                    )
                except OSError as e:
                    logger.debug(
                        "Drive scan error for %s: %s", drive_path, e, exc_info=e
                    )
                    continue

            if self._is_running:
                payload = {"drives": drives}
                self.stats_ready.emit(payload)
                self.finished.emit(payload)
        except (OSError, RuntimeError, ValueError) as e:
            logger.exception("Unexpected error in DriveStatsWorker", exc_info=e)
            self.error.emit(str(e))
            self.finished.emit(None)


class StatCard(Card):
    """Card widget displaying a statistic with icon.

    Renders a labeled value with an icon in a card format.

    Attributes:
        _title: Card title text.
        _value: Displayed value.
        _icon_name: Name of the icon to display.
        _color: Optional accent color.
    """

    def __init__(self, title, value, icon_name, color=None, parent=None):
        """Initialize the stat card.

        Args:
            title: Card title text.
            value: Displayed value.
            icon_name: Name of the SVG icon.
            color: Optional accent color.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._title = title
        self._value = value
        self._icon_name = icon_name
        self._color = color

    def set_value(self, value, color=None):
        """Update the displayed value.

        Args:
            value: New value to display.
            color: Optional new color.
        """
        self._value = str(value)
        if color:
            self._color = color
        self.update()

    def paintEvent(self, e):
        """Paint the stat card.

        Args:
            e: Paint event.
        """
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.window().c if hasattr(self.window(), "c") else Theme.DARK  # type: ignore[union-attr]

        icon_bg = parse_color(c["input_bg"])
        p.setBrush(icon_bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(16, 20, 48, 48, 12, 12)

        icon_col = self._color if self._color else c["accent"]
        icon = svg_icon(self._icon_name, icon_col, 24)
        p.drawPixmap(28, 32, icon)

        p.setPen(parse_color(c["secondary"]))
        p.setFont(QFont(Theme.FONT, 13))
        p.drawText(80, 40, self._title)

        p.setPen(parse_color(c["text"]))
        font = QFont(Theme.FONT, 20)
        font.setBold(True)
        p.setFont(font)
        p.drawText(80, 70, self._value)


class QuickActionCard(Card):
    """Clickable card for navigation to a quick action.

    Provides hover effects and click handling for navigation.

    Attributes:
        clicked: Signal emitted when card is clicked.
        _title: Card title text.
        _subtitle: Card subtitle text.
        _icon_name: Name of the icon to display.
        _hover: Current hover state.
    """

    clicked = Signal()

    def __init__(self, title, subtitle, icon_name, parent=None):
        """Initialize the quick action card.

        Args:
            title: Card title text.
            subtitle: Card subtitle text.
            icon_name: Name of the SVG icon.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(140)
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._title = title
        self._subtitle = subtitle
        self._icon_name = icon_name
        self._hover = False

    def enterEvent(self, e):
        """Handle mouse enter.

        Args:
            e: Enter event.
        """
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        """Handle mouse leave.

        Args:
            e: Leave event.
        """
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        """Handle mouse press.

        Args:
            e: Mouse event.
        """
        self.clicked.emit()

    def paintEvent(self, e):
        """Paint the quick action card.

        Args:
            e: Paint event.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.window().c if hasattr(self.window(), "c") else Theme.DARK  # type: ignore[union-attr]

        rect = self.rect()
        bg = parse_color(c["card"])
        if self._hover:
            bg = parse_color(c.get("hover", c["card"]))
            p.setBrush(bg)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect, Theme.R, Theme.R)

            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(parse_color(c["accent"]))
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), Theme.R, Theme.R)
        else:
            p.setBrush(bg)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect, Theme.R, Theme.R)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(parse_color(c["separator"]))
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), Theme.R, Theme.R)

        circle_bg = parse_color(c["accent"])
        p.setBrush(circle_bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(20, 20, 40, 40)

        icon_col = c["accent_text"]
        icon = svg_icon(self._icon_name, icon_col, 20)
        p.drawPixmap(30, 30, icon)

        p.setPen(parse_color(c["text"]))
        font = p.font()
        font.setPixelSize(16)
        font.setBold(True)
        p.setFont(font)
        p.drawText(20, 85, self._title)

        p.setPen(parse_color(c["secondary"]))
        font.setPixelSize(13)
        font.setBold(False)
        p.setFont(font)
        p.drawText(20, 110, self._subtitle)


class HomePage(QScrollArea):
    """S.O.K application home page.

    Displays drive statistics and quick access navigation cards.

    Attributes:
        navigate: Signal emitted with page index for navigation.
    """

    navigate = Signal(int)

    def __init__(self, parent=None):
        """Initialize the home page.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("Page")
        self._config = get_config_manager()
        self._worker_runner = WorkerRunner(self)

        self._build()
        self.refresh()

    def closeEvent(self, event):
        """Handle page close event.

        Stops background workers before closing.

        Args:
            event: Close event.
        """
        self.stop_workers()
        super().closeEvent(event)

    def _build(self):
        """Build the home page UI."""
        content = QWidget()
        content.setObjectName("PageContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(24)

        header_layout = QHBoxLayout()

        text_layout = QVBoxLayout()
        self.lbl_welcome_title = QLabel()
        self.lbl_welcome_title.setObjectName("PageTitle")
        self.lbl_welcome_title.setStyleSheet(
            "font-size: 24px; font-weight: 700; margin-bottom: 4px;"
        )

        self.lbl_welcome_subtitle = QLabel()
        self.lbl_welcome_subtitle.setStyleSheet(
            "font-size: 14px; opacity: 0.8; color: #8A8A8E;"
        )
        self.lbl_welcome_subtitle.setWordWrap(True)

        text_layout.addWidget(self.lbl_welcome_title)
        text_layout.addWidget(self.lbl_welcome_subtitle)
        header_layout.addLayout(text_layout, 1)

        logo = QLabel()
        logo.setFixedSize(80, 80)
        logo.setScaledContents(True)
        logo_path = ASSETS_DIR / "logo.png"
        if logo_path.exists():
            pm = QPixmap(str(logo_path))
            logo.setPixmap(pm)

        header_layout.addWidget(logo)

        layout.addLayout(header_layout)

        self.status_label = make_section_label("drive_monitors", "DRIVE MONITORS")
        layout.addWidget(self.status_label)

        self.status_container = QWidget()
        self.status_layout = FlowLayout(self.status_container, margin=0, spacing=24)

        layout.addWidget(self.status_container)

        self.actions_label = make_section_label("quick_access", "QUICK ACCESS")
        layout.addWidget(self.actions_label)

        actions_container = QWidget()
        actions_layout = FlowLayout(actions_container, margin=0, spacing=24)

        self.video_btn = QuickActionCard("", "", "video")
        self.video_btn.clicked.connect(lambda: self.navigate.emit(1))
        self.video_btn.setGraphicsEffect(card_shadow())

        self.music_btn = QuickActionCard("", "", "music")
        self.music_btn.clicked.connect(lambda: self.navigate.emit(2))
        self.music_btn.setGraphicsEffect(card_shadow())

        self.book_btn = QuickActionCard("", "", "book")
        self.book_btn.clicked.connect(lambda: self.navigate.emit(3))
        self.book_btn.setGraphicsEffect(card_shadow())

        self.game_btn = QuickActionCard("", "", "game")
        self.game_btn.clicked.connect(lambda: self.navigate.emit(4))
        self.game_btn.setGraphicsEffect(card_shadow())

        actions_layout.addWidget(self.video_btn)
        actions_layout.addWidget(self.music_btn)
        actions_layout.addWidget(self.book_btn)
        actions_layout.addWidget(self.game_btn)

        layout.addWidget(actions_container)

        layout.addStretch()
        self.setWidget(content)
        self.retranslateUi()

    def retranslateUi(self):
        """Update all translatable text in the home page.

        Called after language changes to refresh UI strings.
        """
        self.lbl_welcome_title.setText(tr("welcome_title", "Welcome to S.O.K"))
        self.lbl_welcome_subtitle.setText(
            tr(
                "welcome_subtitle",
                "Storage Organization Kit - Your media library, perfectly organized.",
            )
        )
        self.status_label.setText(tr("drive_monitors", "DRIVE MONITORS"))
        self.actions_label.setText(tr("quick_access", "QUICK ACCESS"))

        self.video_btn._title = tr("videos", "Videos")
        self.video_btn._subtitle = tr(
            "organize_movies_tv", "Organize movies & TV shows"
        )
        self.video_btn.update()

        self.music_btn._title = tr("music", "Music")
        self.music_btn._subtitle = tr("organize_music_library", "Tag your albums")
        self.music_btn.update()

        self.book_btn._title = tr("books", "Books")
        self.book_btn._subtitle = tr("organize_book_collection", "Manage your ebooks")
        self.book_btn.update()

        self.game_btn._title = tr("games", "Games")
        self.game_btn._subtitle = tr("organize_game_library", "Organize your ROMs")
        self.game_btn.update()

        self.refresh()

    def refresh(self):
        """Refresh drive statistics.

        Stops existing workers and starts a new stats collection.
        """
        self.stop_workers()

        worker = StatsWorker(None, None)
        worker.stats_ready.connect(self._on_stats_ready)
        worker.error.connect(lambda e: logger.error("Stats worker error: %s", e))
        self._worker_runner.run(
            worker, lambda _: None, lambda e: logger.error("Stats worker error: %s", e)
        )

    def _on_stats_ready(self, stats):
        """Handle stats worker completion.

        Updates drive status cards with collected data.

        Args:
            stats: Dictionary containing drive statistics.
        """
        self._clear_status_cards()

        drives = stats.get("drives", [])

        if not drives:
            error_card = StatCard(
                tr("error", "Error"),
                tr("no_drive_detected", "No drive detected"),
                "cross",
                "#FF5555",
            )
            error_card.setGraphicsEffect(card_shadow())
            self.status_layout.addWidget(error_card)
            return

        for drive in drives:
            pct = drive["percent_free"]
            if pct > 0.20:
                color = "#50FA7B"
            elif pct > 0.10:
                color = "#FFB86C"
            else:
                color = "#FF5555"

            card = StatCard(
                drive["label"],
                drive["free_str"],
                "settings",
                color,
            )
            card.setGraphicsEffect(card_shadow())
            self.status_layout.addWidget(card)

    def _clear_status_cards(self):
        """Remove all status cards from the layout."""
        while self.status_layout.count():
            item = self.status_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def stop_workers(self):
        """Stop all background workers."""
        self._worker_runner.stop()
