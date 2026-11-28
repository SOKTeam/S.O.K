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
"""Input formats section for settings page, as a dotted sheet.

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
from sok.ui.components.base import KeyButton
from sok.ui.components.settings.layout import ChoiceLine, SheetRow
from sok.ui.i18n import tr
from sok.ui.theme import set_tone

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
    """Input formats section for settings page, as a dotted sheet.

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

        # The help, visible; the variables and default forms in its tooltip.
        self._info = QLabel()
        self._info.setObjectName("SettingHint")
        self._info.setWordWrap(True)
        self._info.setCursor(Qt.CursorShape.WhatsThisCursor)
        layout.addWidget(self._info)
        layout.addSpacing(6)

        self._list = QWidget()
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._rows: List[SheetRow] = []
        layout.addWidget(self._list)
        layout.addSpacing(6)
        layout.addWidget(self._build_add_row())
        layout.addSpacing(8)
        layout.addWidget(self._build_test_row())

    def _build_add_row(self) -> QWidget:
        """The kind as words, then the pattern and the Add key."""
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._kind_line = ChoiceLine([kind for kind, _key, _default in KINDS])
        self._kind = self._kind_line.choice
        self._kind.set_value(KINDS[0][0])
        layout.addWidget(self._kind_line)

        self._error = QLabel()
        set_tone(self._error, "warn")
        self._error.setVisible(False)

        line = QHBoxLayout()
        line.setSpacing(8)
        self._input = QLineEdit()
        self._input.setObjectName("SettingsFormatInput")
        self._input.returnPressed.connect(self._add)
        self._input.textChanged.connect(lambda: self._error.setVisible(False))
        self._add_btn = KeyButton("", small=True)
        self._add_btn.clicked.connect(self._add)
        line.addWidget(self._input, 1)
        line.addWidget(self._add_btn)
        layout.addLayout(line)
        layout.addWidget(self._error)
        return row

    def _build_test_row(self) -> QWidget:
        """A file name to test, and what is read from it."""
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._test_input = QLineEdit()
        self._test_input.setObjectName("SettingsFormatInput")
        self._test_input.textChanged.connect(self._run_test)
        layout.addWidget(self._test_input)
        self._test_result = QLabel()
        self._test_result.setObjectName("SettingHint")
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
        """A line per pattern of the settings: its kind ..... it. A click
        opens it on the key that removes it."""
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()
        self._rows = []
        for kind, _key, _default in KINDS:
            for pattern in self.patterns(kind):
                self._list_layout.addWidget(self._pattern_line(kind, pattern))
        self._list.setVisible(self._list_layout.count() > 0)

    def _pattern_line(self, kind: str, pattern: str) -> SheetRow:
        row = SheetRow(mono_value=True)
        row.name.setText(kind_label(kind))
        row.value.setText(pattern)
        row.value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        remove = KeyButton(tr("remove_pattern", "Remove this pattern"), small=True)
        remove.set_danger(True)
        remove.clicked.connect(lambda _=False: self._remove(kind, pattern))
        keys = QHBoxLayout()
        keys.addWidget(remove)
        keys.addStretch()
        row.details_layout.addLayout(keys)
        row.clicked.connect(lambda r=row: self._open_line(r))
        self._rows.append(row)
        return row

    def _open_line(self, row: SheetRow) -> None:
        opening = not row.is_open()
        for other in self._rows:
            other.set_open(False)
        row.set_open(opening)

    def _add(self) -> None:
        pattern = self._input.text().strip()
        kind = self._kind.value()
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
        self._error.setText(text)
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
        """The variables and the default forms of each kind."""
        blocks: List[str] = []
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
        self._info.setText(
            tr(
                "input_formats_help",
                "Describe how your file names are built, with the variables "
                "of the file names above. Your patterns are tried before the "
                "ones S.O.K knows. {ignore} skips a part of the name.",
            )
        )
        self._info.setToolTip(self._tooltip())
        self._input.setPlaceholderText(tr("input_add_placeholder", "Add a pattern"))
        self._add_btn.setText(tr("add_pattern", "Add"))
        self._test_input.setPlaceholderText(
            tr("input_test_placeholder", "Paste a file name")
        )
        self._kind_line.name.setText(tr("input_kind", "Kind"))
        self._kind.set_texts(tr(key, default) for _kind, key, default in KINDS)
        self._show_patterns()
        self._run_test()
