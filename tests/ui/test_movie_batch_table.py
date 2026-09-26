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
from sok.ui.components.organize.movie_batch_table import MovieBatchTable


class TestMovieBatchTableDrop:
    def test_dropped_folder_is_scanned(self, qtbot, tmp_path):
        (tmp_path / "Movies" / "Sub").mkdir(parents=True)
        (tmp_path / "Movies" / "b.mkv").write_text("")
        (tmp_path / "Movies" / "Sub" / "a.MP4").write_text("")
        (tmp_path / "Movies" / "notes.txt").write_text("")
        loose = tmp_path / "c.mkv"
        loose.write_text("")
        table = MovieBatchTable([".mkv", ".mp4"])
        qtbot.addWidget(table)

        found = table._filter_supported([tmp_path / "Movies", loose])

        assert sorted(p.name for p in found) == ["a.MP4", "b.mkv", "c.mkv"]
