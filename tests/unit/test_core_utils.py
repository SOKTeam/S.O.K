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
from sok.core.utils import format_name, extract_episode_info, is_video_file


class TestCoreUtils:
    def test_format_name(self):
        # Test removing forbidden characters
        assert format_name("file/with|forbidden*chars?") == "filewithforbiddenchars"
        # Test replacing multiple spaces
        assert format_name("file  with   spaces") == "file with spaces"
        # Test mixed
        assert format_name(" cool < file > name ") == " cool file name "

    def test_extract_episode_info(self):
        # Standard format S01E01
        info = extract_episode_info("MyShow.S01E05.720p.mkv")
        assert info is not None
        assert info["name"] == "MyShow."
        assert info["season"] == 1
        assert info["episode"] == 5

        # No match
        assert extract_episode_info("MyMovie.2023.mkv") is None

    def test_is_video_file(self):
        assert is_video_file("movie.mkv") is True
        assert is_video_file("video.mp4") is True
        assert is_video_file("image.jpg") is False
        assert is_video_file("document.txt") is False
