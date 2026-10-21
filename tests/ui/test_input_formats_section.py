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
import pytest
from PySide6.QtWidgets import QLabel

from sok.core import name_patterns
from sok.ui.components.settings.input_formats_section import InputFormatsSection


class FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        self._values[key] = value


@pytest.fixture
def section(qtbot, monkeypatch):
    config = FakeConfig(input_patterns={"movie": ["{title} [{year}]"]})
    # The parsers read the patterns through the config manager.
    monkeypatch.setattr(
        name_patterns,
        "user_patterns",
        lambda kind: config.get("input_patterns", {}).get(kind, []),
    )
    widget = InputFormatsSection(config)
    qtbot.addWidget(widget)
    widget.retranslate()
    widget.load()
    return widget, config


def add(widget, kind, pattern):
    widget._kind.setCurrentIndex(widget._kind.findData(kind))
    widget._input.setText(pattern)
    widget._add()


def listed(widget):
    labels = widget._list.findChildren(QLabel)
    return [lbl.text() for lbl in labels if not lbl.isHidden()]


def test_a_valid_pattern_is_saved_and_listed(section):
    widget, config = section

    add(widget, name_patterns.BOOK, "{title} - {author}")

    assert config.get("input_patterns")["book"] == ["{title} - {author}"]
    assert widget._input.text() == ""
    assert "{title} - {author}" in listed(widget)


def test_an_invalid_pattern_is_refused_with_a_message(section):
    widget, config = section

    add(widget, name_patterns.BOOK, "{title} - {auteur}")

    assert "book" not in config.get("input_patterns")
    assert not widget._error.isHidden()
    assert "{auteur}" in widget._error.text()


def test_a_pattern_already_listed_is_refused(section):
    widget, config = section

    add(widget, name_patterns.MOVIE, "{title} [{year}]")

    assert config.get("input_patterns")["movie"] == ["{title} [{year}]"]
    assert not widget._error.isHidden()


def test_removing_the_last_pattern_of_a_kind_drops_it(section):
    widget, config = section

    widget._remove(name_patterns.MOVIE, "{title} [{year}]")

    assert config.get("input_patterns") == {}
    assert widget._list.isHidden()


def test_the_test_field_says_which_pattern_read_the_name(section):
    widget, _ = section

    widget._test_input.setText("Apollo 13 [1995].mkv")

    text = widget._test_result.text()
    assert "{title} = Apollo 13" in text
    assert "{year} = 1995" in text
    assert "{title} [{year}]" in text


def test_the_test_field_needs_an_extension(section):
    widget, _ = section

    widget._test_input.setText("Apollo 13 [1995]")

    assert "(.mkv" in widget._test_result.text()


def test_the_default_forms_are_in_the_tooltip(section):
    widget, _ = section

    assert "{title} S{season}E{episode}" in widget._info.toolTip()
