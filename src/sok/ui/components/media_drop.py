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
A file dropped on the home page whose type is a guess.

The detector is not sure of it (an .iso can be a game or a video disc): the
row shows why and lets the user choose its type.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sok.core.interfaces import ContentType
from sok.file_operations.detection import (
    DetectedFile,
)
from sok.ui.components.base import ActionButton
from sok.ui.components.inputs import ModernComboBox
from sok.ui.i18n import tr

# Kinds in the order of the type menu of a file to check.
KINDS = [
    ContentType.MOVIE,
    ContentType.EPISODE,
    ContentType.ALBUM,
    ContentType.TRACK,
    ContentType.BOOK,
    ContentType.GAME,
]


def kind_label(kind: ContentType) -> str:
    """Name of the page that organizes a kind of file."""
    return {
        ContentType.MOVIE: tr("movies", "Movies"),
        ContentType.EPISODE: tr("tv_shows", "TV Shows"),
        ContentType.ALBUM: tr("albums", "Albums"),
        ContentType.TRACK: tr("tracks", "Tracks"),
        ContentType.BOOK: tr("books", "Books"),
        ContentType.GAME: tr("games", "Games"),
    }[kind]


def reason_label(reason: str) -> str:
    """Explain to the user why a file must be checked."""
    return {
        "episode number without season": tr(
            "drop_reason_weak_episode", "Episode number without a season"
        ),
        "season folder without episode number": tr(
            "drop_reason_season_folder", "In a season folder, without an episode number"
        ),
        "video next to episodes": tr(
            "drop_reason_among_episodes", "Video among episodes: a bonus?"
        ),
        "disc image": tr(
            "drop_reason_disc_image", "Disc image: a game or a video disc?"
        ),
    }.get(reason, reason)


class CheckRow(QWidget):
    """A file to check: name, reason, a type menu and an Add button."""

    confirmed = Signal(object)

    def __init__(self, item: DetectedFile, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        texts = QVBoxLayout()
        texts.setSpacing(2)
        name_lbl = QLabel(item.path.name)
        name_lbl.setObjectName("RowTitle")
        name_lbl.setToolTip(str(item.path))
        name_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        texts.addWidget(name_lbl)
        reason_lbl = QLabel(reason_label(item.reason))
        reason_lbl.setObjectName("EmptyState")
        texts.addWidget(reason_lbl)
        layout.addLayout(texts, 1)

        self._combo = ModernComboBox()
        for kind in KINDS:
            self._combo.addItem(kind_label(kind), kind)
        self._combo.setCurrentIndex(KINDS.index(item.kind))
        layout.addWidget(self._combo)

        btn = ActionButton(tr("drop_add", "Add"), small=True)
        btn.clicked.connect(lambda: self.confirmed.emit(self._combo.currentData()))
        layout.addWidget(btn)
