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
from sok.file_operations.music_operations import MusicFileOperations
from sok.file_operations.book_operations import BookFileOperations
from sok.file_operations.base_operations import BaseFileOperations


class TestMusicAndBookIntegration:
    @pytest.fixture()
    def workspace(self, tmp_path):
        root = tmp_path / "workspace"
        root.mkdir()
        return root

    def test_music_rename_and_move(self, workspace):
        ops = MusicFileOperations()
        src = workspace / "01. track name.mp3"
        src.write_text("audio")

        new_name = ops.generate_new_filename(None, src.name)
        dest = workspace / new_name

        assert BaseFileOperations.safe_move(str(src), str(dest)) is True
        assert dest.exists()
        assert dest.name.startswith("01 - track name")

    def test_book_rename_and_move(self, workspace):
        ops = BookFileOperations()
        src = workspace / "The Way of Kings - Brandon Sanderson.epub"
        src.write_text("ebook")

        new_name = ops.generate_new_filename(None, src.name)
        dest = workspace / new_name

        assert BaseFileOperations.safe_move(str(src), str(dest)) is True
        assert dest.exists()
        assert dest.name.startswith("Brandon Sanderson - The Way of Kings")
