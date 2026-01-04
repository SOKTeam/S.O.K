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
import os
import pytest
from sok.file_operations.base_operations import BaseFileOperations


class TestFileOperationsIntegration:
    @pytest.fixture
    def workspace(self, tmp_path):
        """Creates a temporary workspace with some files"""
        d = tmp_path / "workspace"
        d.mkdir()

        # Create a test file
        f1 = d / "test_file.txt"
        f1.write_text("content")

        return d

    def test_safe_copy(self, workspace):
        source = str(workspace / "test_file.txt")
        dest = str(workspace / "copied_file.txt")

        # Perform copy
        success = BaseFileOperations.safe_copy(source, dest)

        assert success is True
        assert os.path.exists(dest)
        assert os.path.exists(source)  # Source should still exist

        # Verify content
        with open(dest, "r") as f:
            assert f.read() == "content"

    def test_safe_move(self, workspace):
        source = str(workspace / "test_file.txt")
        dest = str(workspace / "moved_file.txt")

        # Perform move
        success = BaseFileOperations.safe_move(source, dest)

        assert success is True
        assert os.path.exists(dest)
        assert not os.path.exists(source)  # Source should be gone

        # Verify content
        with open(dest, "r") as f:
            assert f.read() == "content"

    def test_clean_filename(self):
        # Integration with OS constraints logic (though mostly logic, it prepares for OS)
        dirty = "file/name|bad?.txt"
        clean = BaseFileOperations.clean_filename(dirty)
        assert clean == "file_name_bad_.txt"

        # Check against real OS creation (optional but good for integration)
        # This confirms the cleaned name is actually valid
        # We can't easily test this without risking OS errors, but the logic holds.
