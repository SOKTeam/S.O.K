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
from pathlib import Path

from PySide6.QtWidgets import QLabel, QPushButton

from sok.core.interfaces import ContentType
from sok.file_operations.detection import MediaTypeDetector
from sok.ui.components.media_drop import DropSummary
from sok.ui.i18n import tr

OPEN = tr("drop_open", "Open")
ADD = tr("drop_add", "Add")
CLEAR = tr("drop_clear", "Clear")
TO_CHECK = tr("drop_to_check", "To check")


def make(root: Path, *names: str) -> None:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")


def texts(widget) -> list:
    return [lbl.text() for lbl in widget.findChildren(QLabel)]


def buttons(widget, text: str) -> list:
    return [b for b in widget.findChildren(QPushButton) if b.text() == text]


def summary_for(qtbot, root: Path):
    detector = MediaTypeDetector()
    summary = DropSummary(detector)
    qtbot.addWidget(summary)
    summary.set_report(detector.detect_sources([root]))
    return summary


def test_each_group_has_an_open_button(qtbot, tmp_path):
    make(tmp_path, "Dune (2021).mkv", "Heat (1995).mkv", "Andor/Andor S01E01.mkv")
    summary = summary_for(qtbot, tmp_path)

    assert "Andor" in texts(summary)
    assert len(buttons(summary, OPEN)) == 2

    with qtbot.waitSignal(summary.open_requested) as signal:
        buttons(summary, OPEN)[0].click()
    group, files = signal.args
    assert group.kind == ContentType.MOVIE
    assert [f.name for f in files] == ["Dune (2021).mkv", "Heat (1995).mkv"]


def test_an_organized_group_is_marked_done(qtbot, tmp_path):
    make(tmp_path, "Movies/Dune (2021).mkv", "Andor S01E01.mkv", "Andor S01E02.mkv")
    summary = summary_for(qtbot, tmp_path)

    (tmp_path / "Movies/Dune (2021).mkv").unlink()
    (tmp_path / "Andor S01E01.mkv").unlink()
    summary.refresh()

    assert tr("drop_done", "✓ Organized") in texts(summary)
    assert tr("drop_remaining", "{count} of {total} left").format(
        count=1, total=2
    ) in texts(summary)
    assert len(buttons(summary, OPEN)) == 1


def test_a_file_to_check_is_added_with_the_chosen_type(qtbot, tmp_path):
    make(tmp_path, "Halo (USA).iso")
    summary = summary_for(qtbot, tmp_path)
    assert TO_CHECK in texts(summary)
    assert buttons(summary, OPEN) == []

    buttons(summary, ADD)[0].click()

    assert TO_CHECK not in texts(summary)
    assert tr("games", "Games") in texts(summary)
    assert len(buttons(summary, OPEN)) == 1


def test_nothing_recognized_lists_the_accepted_files(qtbot, tmp_path):
    make(tmp_path, "notes.txt")
    summary = summary_for(qtbot, tmp_path)

    [message] = [t for t in texts(summary) if ".mkv" in t]
    assert ".epub" in message


def test_clear_hides_the_summary(qtbot, tmp_path):
    make(tmp_path, "Dune (2021).mkv", "Andor/Andor S01E01.mkv")
    summary = summary_for(qtbot, tmp_path)
    summary.show()

    buttons(summary, CLEAR)[0].click()

    assert not summary.isVisible()
