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
"""Input formats section for settings page.

Lets users describe how their file names are built, with patterns such as
"{artist} - {year} - {album} - {track} - {title}" (see
sok.core.name_patterns), and test a file name against them.
"""

import html
import os
from typing import Any, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sok.core import name_patterns
from sok.core.name_patterns import BUILTIN, VARIABLES, PatternError, check_pattern
from sok.file_operations import (
    BookFileOperations,
    GameFileOperations,
    MusicFileOperations,
    VideoFileOperations,
)
from sok.ui.components.base import ActionButton, Card
from sok.ui.components.inputs import ModernComboBox
from sok.ui.controllers.ui_helpers import make_section_label
from sok.ui.i18n import tr
from sok.ui.theme import card_shadow, set_tone

# Kinds of names, with the translation key and default of their label.
KINDS = [
    (name_patterns.EPISODE, "tv_series", "TV Series"),
    (name_patterns.MOVIE, "movie", "Movies"),
    (name_patterns.MUSIC, "music", "Music"),
    (name_patterns.BOOK, "book", "Book"),
    (name_patterns.GAME, "game", "Game"),
]

# Values shown by the test field: (variable, key of the parsed info).
TEST_FIELDS = {
    name_patterns.EPISODE: [
        ("title", "title"),
        ("season", "season"),
        ("episode", "episode"),
        ("episode_title", "episode_title"),
        ("year", "year"),
    ],
    name_patterns.MOVIE: [("title", "title"), ("year", "year")],
    name_patterns.MUSIC: [
        ("artist", "artist"),
        ("album", "album"),
        ("disc", "disc_number"),
        ("track", "track_number"),
        ("title", "title"),
        ("year", "year"),
    ],
    name_patterns.BOOK: [
        ("author", "author"),
        ("title", "title"),
        ("series", "series"),
        ("series_number", "series_number"),
        ("year", "year"),
    ],
    name_patterns.GAME: [
        ("title", "title"),
        ("platform", "platform"),
        ("region", "region"),
        ("year", "year"),
    ],
}

# The test field finds the type of a name from its extension; the first
# parser that takes it wins.
PARSERS = [
    ("video", VideoFileOperations),
    (name_patterns.MUSIC, MusicFileOperations),
    (name_patterns.BOOK, BookFileOperations),
    (name_patterns.GAME, GameFileOperations),
]


def kind_label(kind: str) -> str:
    """Translated label of a kind of name."""
    for key, tr_key, default in KINDS:
        if key == kind:
            return tr(tr_key, default)
    return kind


def pattern_error_text(error: PatternError) -> str:
    """Translated message for a pattern that cannot be used."""
    name = "{" + error.name + "}"
    if error.code == "unknown":
        return tr("pattern_error_unknown", "Unknown variable: {name}").format(name=name)
    if error.code == "twice":
        return tr("pattern_error_twice", "{name} is used twice").format(name=name)
    if error.code == "required":
        return tr("pattern_error_required", "The pattern needs {name}").format(
            name=name
        )
    return tr("pattern_error_braces", "A brace { or } is not closed.")


class InputFormatsSection(QWidget):
    """Input formats section for settings page.

    One card: the user's patterns, a line to add one, and a field to test a
    file name. The variables and the forms S.O.K reads by default are in
    the tooltip of the ⓘ next to the title.
    """

    def __init__(self, config, parent=None):
        """Initialize the input formats section.

        Args:
            config: Configuration manager instance.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._config = config
        self._ops: Dict[str, Any] = {}
        self._build()

    def _build(self):
        """Build the section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(6)
        self.label = make_section_label("input_formats", "Input Formats")
        self._info = QLabel("ⓘ")
        self._info.setObjectName("SectionLabel")
        self._info.setCursor(Qt.CursorShape.WhatsThisCursor)
        header.addWidget(self.label)
        header.addWidget(self._info)
        header.addStretch()
        layout.addLayout(header)

        card = Card()
        self._list = QWidget()
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        card.add(self._list)
        card.add(self._build_add_row())
        card.add(self._build_test_row())

        card.setGraphicsEffect(card_shadow())
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(card)

    def _build_add_row(self) -> QWidget:
        """Row with a kind, a pattern and the Add button."""
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self._error = QLabel()
        # Same look as the "API key required" warnings: red is not readable
        # on the orange theme.
        self._error.setStyleSheet("font-size: 11px; font-weight: bold;")
        set_tone(self._error, "warn")
        self._error.setVisible(False)

        line = QHBoxLayout()
        self._kind = ModernComboBox()
        self._kind.setObjectName("SettingsCombo")
        self._kind.setMinimumWidth(110)
        self._input = QLineEdit()
        self._input.setObjectName("SettingsFormatInput")
        self._input.returnPressed.connect(self._add)
        self._input.textChanged.connect(lambda: self._error.setVisible(False))
        self._add_btn = ActionButton()
        self._add_btn.clicked.connect(self._add)
        line.addWidget(self._kind)
        line.addWidget(self._input, 1)
        line.addWidget(self._add_btn)
        layout.addLayout(line)
        layout.addWidget(self._error)
        return row

    def _build_test_row(self) -> QWidget:
        """Row with a file name and what is read from it."""
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        line = QHBoxLayout()
        self._test_title = QLabel()
        self._test_title.setObjectName("RowTitle")
        self._test_title.setMinimumWidth(110)
        self._test_input = QLineEdit()
        self._test_input.setObjectName("SettingsFormatInput")
        self._test_input.textChanged.connect(self._run_test)
        line.addWidget(self._test_title)
        line.addWidget(self._test_input, 1)
        layout.addLayout(line)

        self._test_result = QLabel()
        self._test_result.setObjectName("RowSubtitle")
        self._test_result.setWordWrap(True)
        self._test_result.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._test_result.setVisible(False)
        layout.addWidget(self._test_result)
        return row

    def _saved(self) -> Dict[str, Any]:
        saved = self._config.get("input_patterns", {})
        return dict(saved) if isinstance(saved, dict) else {}

    def patterns(self, kind: str) -> List[str]:
        """Patterns of the settings for a kind of name."""
        patterns = self._saved().get(kind, [])
        return list(patterns) if isinstance(patterns, list) else []

    def save_patterns(self, kind: str, patterns: List[str]) -> None:
        """Save the patterns of a kind and show the list again."""
        saved = self._saved()
        if patterns:
            saved[kind] = patterns
        else:
            saved.pop(kind, None)
        self._config.set("input_patterns", saved)
        self._show_patterns()
        self._run_test()

    def _show_patterns(self) -> None:
        """One line per pattern of the settings: its kind, it, a remove button."""
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()
        for kind, _key, _default in KINDS:
            for pattern in self.patterns(kind):
                self._list_layout.addWidget(self._pattern_line(kind, pattern))
        self._list.setVisible(self._list_layout.count() > 0)

    def _pattern_line(self, kind: str, pattern: str) -> QWidget:
        line = QWidget()
        line.setFixedHeight(32)
        layout = QHBoxLayout(line)
        layout.setContentsMargins(12, 0, 12, 0)
        kind_lbl = QLabel(kind_label(kind))
        kind_lbl.setObjectName("RowSubtitle")
        kind_lbl.setMinimumWidth(110)
        pattern_lbl = QLabel(pattern)
        pattern_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        remove = QPushButton("×")
        remove.setObjectName("PatternRemoveBtn")
        remove.setFixedSize(20, 20)
        remove.setCursor(Qt.CursorShape.PointingHandCursor)
        remove.setToolTip(tr("remove_pattern", "Remove this pattern"))
        remove.clicked.connect(lambda _=False: self._remove(kind, pattern))
        layout.addWidget(kind_lbl)
        layout.addWidget(pattern_lbl, 1)
        layout.addWidget(remove)
        return line

    def _add(self) -> None:
        pattern = self._input.text().strip()
        kind = self._kind.currentData()
        if not pattern or not kind:
            return
        error = check_pattern(kind, pattern)
        if error:
            self._show_error(pattern_error_text(error))
            return
        patterns = self.patterns(kind)
        if pattern in patterns:
            self._show_error(
                tr("pattern_exists", "This pattern is already in the list")
            )
            return
        self.save_patterns(kind, [*patterns, pattern])
        self._input.clear()

    def _remove(self, kind: str, pattern: str) -> None:
        self.save_patterns(kind, [p for p in self.patterns(kind) if p != pattern])

    def _show_error(self, text: str) -> None:
        self._error.setText(f"⚠ {text}")
        self._error.setVisible(True)

    def _parser(self, filename: str):
        """Kind and file operations that read a name, from its extension."""
        extension = os.path.splitext(filename)[1].lower()
        for kind, ops_class in PARSERS:
            if kind not in self._ops:
                self._ops[kind] = ops_class()
            if extension in self._ops[kind].supported_extensions:
                return kind, self._ops[kind]
        return None, None

    def _run_test(self, *_args) -> None:
        """Show what is read from the file name of the test field."""
        name = self._test_input.text().strip()
        if not name:
            self._test_result.setVisible(False)
            return
        kind, ops = self._parser(name)
        if ops is None:
            self._test_result.setText(
                tr(
                    "input_test_no_type",
                    "Add the extension of the file (.mkv, .mp3, .epub…)",
                )
            )
            self._test_result.setVisible(True)
            return
        info = ops.extract_info_from_filename(name)
        if kind == "video":
            series = info.get("type") == "series"
            kind = name_patterns.EPISODE if series else name_patterns.MOVIE
        parts = [kind_label(kind)]
        for variable, key in TEST_FIELDS[kind]:
            value = info.get(key)
            if value not in (None, "", []):
                parts.append(f"{{{variable}}} = {value}")
        if info.get("pattern"):
            source = tr(
                "input_test_pattern", "Read with your pattern {pattern}"
            ).format(pattern=info["pattern"])
        else:
            source = tr("input_test_builtin", "Read by the default rules")
        self._test_result.setText("  ·  ".join(parts) + "\n" + source)
        self._test_result.setVisible(True)

    def _tooltip(self) -> str:
        """Help, then the variables and the default forms of each kind."""
        blocks = [
            html.escape(
                tr(
                    "input_formats_help",
                    "Describe how your file names are built, with the variables "
                    "of the output formats. Your patterns are tried before the "
                    "ones S.O.K knows. {ignore} skips a part of the name.",
                )
            )
        ]
        for kind, _key, _default in KINDS:
            variables = [*VARIABLES[kind], name_patterns.IGNORE]
            # One form per line: on one line they cannot be told apart.
            builtin = tr("input_builtin", "Recognized by default: {forms}").format(
                forms=""
            )
            forms = "".join(
                f"<br>&nbsp;&nbsp;•&nbsp;{html.escape(form)}" for form in BUILTIN[kind]
            )
            blocks.append(
                f"<b>{html.escape(kind_label(kind))}</b><br>"
                + html.escape("Variables: " + ", ".join(f"{{{v}}}" for v in variables))
                + "<br>"
                + html.escape(builtin.rstrip())
                + forms
            )
        return "<p>" + "<br><br>".join(blocks) + "</p>"

    def load(self):
        """Load settings values into UI."""
        self._show_patterns()
        self._run_test()

    def retranslate(self):
        """Update translatable UI text."""
        self.label.setText(tr("input_formats", "Input Formats"))
        self._info.setToolTip(self._tooltip())
        self._input.setPlaceholderText(tr("input_add_placeholder", "Add a pattern"))
        self._add_btn.setText(tr("add_pattern", "Add"))
        self._test_title.setText(tr("input_test", "Test"))
        self._test_input.setPlaceholderText(
            tr("input_test_placeholder", "Paste a file name")
        )
        current = self._kind.currentData()
        self._kind.clear()
        for kind, tr_key, default in KINDS:
            self._kind.addItem(tr(tr_key, default), kind)
        self._kind.setCurrentIndex(max(self._kind.findData(current), 0))
        self._show_patterns()
        self._run_test()
