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

    def test_following_the_system_saves_it_and_locks_dark_mode(self, section):
        widget, config = section
        emitted = []
        widget.theme_changed.connect(emitted.append)

        widget._on_system_theme_change(True)

        assert config.get("theme") == "system"
        assert emitted == [True]
        assert widget.toggle.isChecked()
        assert not widget.toggle.isEnabled()

    def test_leaving_system_mode_keeps_the_current_look(self, section):
        widget, config = section
        widget._on_system_theme_change(True)

        widget._on_system_theme_change(False)

        assert config.get("theme") == "dark"
        assert widget.toggle.isEnabled()

    def test_no_system_row_on_other_platforms(self, qtbot, monkeypatch):
        monkeypatch.setattr(appearance_section, "IS_MACOS", False)
        widget = AppearanceSection(FakeConfig(theme="dark"))
        qtbot.addWidget(widget)

        assert widget.system_toggle is None


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
