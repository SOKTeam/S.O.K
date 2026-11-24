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

from sok.ui import platform, theme
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
        return ["en"]


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


class TestAppearanceSectionOnMacOS:
    @pytest.fixture
    def section(self, qtbot, monkeypatch, system_dark):
        monkeypatch.setattr(appearance_section, "IS_MACOS", True)
        config = FakeConfig(theme="light", language="en")
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

    def test_no_accent_box_on_other_platforms(self, qtbot, monkeypatch):
        monkeypatch.setattr(appearance_section, "IS_MACOS", False)
        widget = AppearanceSection(FakeConfig(theme="dark"))
        qtbot.addWidget(widget)

        assert widget.accent_toggle is None


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


class TestAccentColor:
    @pytest.fixture
    def system_accent(self, monkeypatch):
        monkeypatch.setattr(theme, "IS_MACOS", True)
        monkeypatch.setattr(theme, "system_accent_color", lambda: "#0a60ff")

    def test_coral_accent_by_default(self, system_accent):
        assert theme.palette(dark=True)["accent"] == theme.Theme.DARK["accent"]

    def test_system_accent_replaces_coral(self, system_accent):
        c = theme.palette(dark=False, system_accent=True)

        assert c["accent"] == "#0a60ff"
        assert c["accent_text"] == "#FFFFFF"
        assert theme.Theme.LIGHT["accent"] != "#0a60ff"

    def test_system_accent_is_ignored_on_other_platforms(
        self, system_accent, monkeypatch
    ):
        monkeypatch.setattr(theme, "IS_MACOS", False)

        c = theme.palette(dark=True, system_accent=True)

        assert c["accent"] == theme.Theme.DARK["accent"]

    def test_toggle_saves_the_setting_and_restyles(
        self, qtbot, monkeypatch, system_dark
    ):
        monkeypatch.setattr(appearance_section, "IS_MACOS", True)
        config = FakeConfig(theme="dark", language="en")
        widget = AppearanceSection(config)
        qtbot.addWidget(widget)
        widget.load()
        emitted = []
        widget.theme_changed.connect(emitted.append)

        widget._on_accent_change(True)

        assert config.get("use_system_accent") is True
        assert emitted == [True]
