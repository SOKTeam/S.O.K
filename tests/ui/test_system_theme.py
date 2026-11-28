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

from sok.ui import platform
from sok.ui.components.settings import appearance_section
from sok.ui.components.settings.appearance_section import AppearanceSection


class FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        self._values[key] = value

    def get_available_languages(self):
        return ["fr", "en"]


@pytest.fixture
def system_dark(monkeypatch):
    state = {"dark": True}
    monkeypatch.setattr(platform, "system_prefers_dark", lambda: state["dark"])
    monkeypatch.setattr(
        appearance_section, "system_prefers_dark", lambda: state["dark"]
    )
    return state


class TestIsDarkTheme:
    @pytest.mark.parametrize(
        "theme, system, expected",
        [
            ("dark", False, True),
            ("light", True, False),
            ("orange", True, False),
            ("system", True, True),
            ("system", False, False),
        ],
    )
    def test_resolution(self, system_dark, theme, system, expected):
        system_dark["dark"] = system

        assert platform.is_dark_theme(theme) is expected


class TestAppearanceSection:
    @pytest.fixture
    def section(self, qtbot, monkeypatch, system_dark):
        config = FakeConfig(theme="light", language="fr")
        widget = AppearanceSection(config)
        qtbot.addWidget(widget)
        widget.load()
        return widget, config

    def test_choosing_system_saves_it_and_shows_the_system_look(self, section):
        widget, config = section
        emitted = []
        widget.theme_changed.connect(emitted.append)

        widget._on_theme_choice("system")

        assert config.get("theme") == "system"
        assert emitted == [True]

    def test_choosing_dark_or_light_saves_it(self, section):
        widget, config = section
        emitted = []
        widget.theme_changed.connect(emitted.append)

        widget._on_theme_choice("dark")
        widget._on_theme_choice("light")

        assert config.get("theme") == "light"
        assert emitted == [True, False]

    def test_the_saved_theme_is_the_chosen_key(self, section):
        widget, config = section
        config.set("theme", "orange")  # the dropped orange theme reads as light

        widget.load()

        assert widget.theme_choice.value() == "light"

    def test_clicking_a_key_chooses_its_theme(self, section):
        widget, config = section

        widget.theme_choice._click("system")

        assert config.get("theme") == "system"
        assert widget.theme_choice.value() == "system"

    def test_choosing_a_language_saves_it_and_shows_its_name(self, section):
        widget, config = section
        emitted = []
        widget.language_changed.connect(emitted.append)

        widget.lang_choice._click("en")

        assert config.get("language") == "en"
        assert emitted == ["en"]
        assert widget._lang_row.value.text() == "English"


class TestApplyColorScheme:
    @pytest.fixture
    def hints(self, qapp, monkeypatch):
        monkeypatch.setattr(platform, "IS_MACOS", True)
        hints = qapp.styleHints()
        yield hints
        hints.setColorScheme(platform.Qt.ColorScheme.Unknown)

    @pytest.mark.parametrize(
        "theme, expected",
        [
            ("dark", platform.Qt.ColorScheme.Dark),
            ("light", platform.Qt.ColorScheme.Light),
            ("orange", platform.Qt.ColorScheme.Light),
        ],
    )
    def test_forced_theme_overrides_the_native_chrome(
        self, hints, monkeypatch, theme, expected
    ):
        calls = []
        monkeypatch.setattr(hints, "setColorScheme", calls.append)

        platform.apply_color_scheme(theme)

        assert calls == [expected]

    def test_system_theme_removes_the_override(self, hints, monkeypatch):
        calls = []
        monkeypatch.setattr(hints, "setColorScheme", calls.append)

        platform.apply_color_scheme("system")

        assert calls == [platform.Qt.ColorScheme.Unknown]

    def test_does_nothing_on_other_platforms(self, hints, monkeypatch):
        monkeypatch.setattr(platform, "IS_MACOS", False)
        calls = []
        monkeypatch.setattr(hints, "setColorScheme", calls.append)

        platform.apply_color_scheme("dark")

        assert calls == []


class TestSrgbWindows:
    @pytest.fixture
    def default_format(self):
        from PySide6.QtGui import QSurfaceFormat

        saved = QSurfaceFormat.defaultFormat()
        yield QSurfaceFormat
        QSurfaceFormat.setDefaultFormat(saved)

    def test_windows_are_tagged_srgb_on_macos(self, default_format, monkeypatch):
        from PySide6.QtGui import QColorSpace

        monkeypatch.setattr(platform, "IS_MACOS", True)

        platform.use_srgb_windows()

        space = default_format.defaultFormat().colorSpace()
        assert space == QColorSpace(QColorSpace.NamedColorSpace.SRgb)

    def test_nothing_changes_on_other_platforms(self, default_format, monkeypatch):
        monkeypatch.setattr(platform, "IS_MACOS", False)
        before = default_format.defaultFormat().colorSpace()

        platform.use_srgb_windows()

        assert default_format.defaultFormat().colorSpace() == before
