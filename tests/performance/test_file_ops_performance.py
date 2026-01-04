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
import time
from sok.file_operations.base_operations import BaseFileOperations


class TestFileOperationsPerformance:
    @pytest.fixture
    def large_dataset(self, tmp_path):
        """Creates a dataset with many files to simulate a large library."""
        base_dir = tmp_path / "large_library"
        base_dir.mkdir()

        file_count = 1000  # Adjustable load

        # Create dummy files
        for i in range(file_count):
            # Create some duplicates every 10 files
            content = f"content_{i % (file_count // 10)}"
            p = base_dir / f"file_{i}.txt"
            p.write_text(content)

        return str(base_dir)

    def test_find_duplicates_performance(self, large_dataset):
        """
        Benchmark the find_duplicates operation.
        Performance Budget: Should process 1000 files in under 2 seconds (arbitrary baseline).
        """
        start_time = time.perf_counter()

        # Execute the heavy operation
        duplicates = BaseFileOperations.find_duplicates(
            directory=large_dataset,
            extensions=[".txt"],
            recursive=False,
            by_hash=True,  # This forces file reading, so it's I/O intensive
        )

        end_time = time.perf_counter()
        duration = end_time - start_time

        # Log performance metrics (visible if pytest is run with -s)
        print(f"\nPerformance: Scanned 1000 files in {duration:.4f} seconds.")

        # Assertions
        assert len(duplicates) > 0
        # Check if it meets the performance budget
        # Note: Timeouts in tests can be flaky on CI, but useful for local baselines.
        assert (
            duration < 2.0
        ), f"Performance degradation: took {duration}s, expected < 2.0s"

    def test_directory_size_performance(self, large_dataset):
        """Benchmark calculating directory size for a large structure."""
        start_time = time.perf_counter()

        size = BaseFileOperations.get_directory_size(large_dataset)

        end_time = time.perf_counter()
        duration = end_time - start_time

        print(
            f"\nPerformance: Calculated size of 1000 files in {duration:.4f} seconds."
        )

        assert size > 0
        assert duration < 0.5, f"Directory size calculation too slow: {duration}s"
