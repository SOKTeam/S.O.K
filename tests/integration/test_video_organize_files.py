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
from sok.core.media_manager import UniversalMediaManager
from sok.file_operations.video_operations import VideoFileOperations
from sok.media.video.movie import Movie


class TestVideoOrganizeFiles:
    def test_uppercase_extensions_are_found(self, tmp_path):
        source = tmp_path / "downloads"
        source.mkdir()
        (source / "MATRIX.1999.MKV").write_text("")
        (source / "notes.txt").write_text("")
        movie = Movie("The Matrix", "en", UniversalMediaManager())
        movie.year = 1999

        report = VideoFileOperations().organize_files(
            str(source),
            str(tmp_path / "library"),
            movie,
            dry_run=True,
            progress_callback=lambda *_: None,
        )

        assert report["total_files"] == 1
        assert report["total_moved"] == 1
