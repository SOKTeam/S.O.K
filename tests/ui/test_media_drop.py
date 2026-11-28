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
from datetime import date, datetime
from pathlib import Path

from sok.core.interfaces import ContentType
from sok.file_operations.detection import MediaTypeDetector
from sok.ui.i18n import tr
from sok.ui.pages.home_page import HomePage, when_text


def make(root: Path, *names: str) -> None:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")


def test_each_group_is_sent_to_its_page(qtbot, tmp_path):
    make(tmp_path, "Dune (2021).mkv", "Andor/Andor S01E01.mkv")
    home = HomePage()
    qtbot.addWidget(home)
    sent = []
    home.open_group.connect(
        lambda group, files: sent.append((group.kind.value, len(files)))
    )

    home._on_analyzed(MediaTypeDetector().detect_sources([tmp_path]))

    assert sorted(sent) == sorted(
        [(ContentType.MOVIE.value, 1), (ContentType.EPISODE.value, 1)]
    )


def test_a_file_to_check_goes_to_the_chosen_type(qtbot, tmp_path):
    make(tmp_path, "Halo (USA).iso")
    home = HomePage()
    qtbot.addWidget(home)
    sent = []
    home.open_group.connect(lambda group, files: sent.append((group.kind, files)))
    home._on_analyzed(MediaTypeDetector().detect_sources([tmp_path]))
    assert sent == []
    [row] = home._report.to_check

    home._confirm(row, ContentType.GAME)

    assert sent == [(ContentType.GAME, [tmp_path / "Halo (USA).iso"])]
    assert home._report.to_check == []


def test_when_text():
    today = date(2026, 11, 24)

    assert when_text(datetime(2026, 11, 24, 21, 42), today) == tr(
        "home_today_at", "today at {0}"
    ).format("21:42")
    assert when_text(datetime(2026, 11, 23, 9, 5), today) == tr(
        "home_yesterday_at", "yesterday at {0}"
    ).format("09:05")
    assert "12/11" in when_text(datetime(2026, 11, 12, 8, 0), today)


def test_a_drop_runs_the_detection_in_the_background(qtbot, tmp_path):
    make(tmp_path, "Dune (2021).mkv")
    home = HomePage()
    qtbot.addWidget(home)
    sent = []
    home.open_group.connect(lambda group, files: sent.append(files))

    home._analyze([tmp_path])

    qtbot.waitUntil(lambda: sent == [[tmp_path / "Dune (2021).mkv"]], timeout=5000)
