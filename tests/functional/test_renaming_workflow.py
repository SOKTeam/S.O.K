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
from sok.file_operations.base_operations import BaseFileOperations
from sok.core.utils import format_name


class TestRenamingWorkflow:
    def test_rename_workflow(self, tmp_path):
        """
        Simulates a user workflow:
        1. Identify a file with a messy name.
        2. Clean the name.
        3. Rename the file safely.
        4. Verify.
        """
        # Setup
        # Create file with "safe" name first because Windows won't let us create the messy one easily
        # to simulate the "messy" starting point, we'll assume the file exists on disk
        # but maybe with a slightly less invalid name for the test runtime on Windows,
        # OR we just test the logic flow on a file that NEEDS cleaning (e.g. multiple spaces).

        # Windows file systems don't allow < > | etc. so we can't create that file to start with.
        # We'll use multiple spaces and dots which is allowed but "messy".
        start_name = "My  Messy...File.txt"
        start_path = tmp_path / start_name
        start_path.write_text("important data")

        # 1. User selects file
        current_path = str(start_path)
        assert os.path.exists(current_path)

        # 2. Logic determines new name
        # We use format_name from core.utils for the logic
        new_name_candidate = format_name(start_name)
        # format_name replaces '  ' with ' ' and removes bad chars.
        # "My  Messy...File.txt" -> "My Messy...File.txt" (simple spaces)
        # Actually format_name implementation: re.sub(' +', ' ', re.sub(r'[<>:"/\\|?*]', '', name))
        # It doesn't remove dots.

        expected_name = "My Messy...File.txt"

        # 3. Apply Rename using BaseFileOperations
        new_path = str(tmp_path / expected_name)

        success = BaseFileOperations.safe_move(current_path, new_path)

        # 4. Verify
        assert success is True
        assert not os.path.exists(current_path)
        assert os.path.exists(new_path)
        assert new_name_candidate == expected_name

        # Verify content integrity
        with open(new_path, "r") as f:
            assert f.read() == "important data"
