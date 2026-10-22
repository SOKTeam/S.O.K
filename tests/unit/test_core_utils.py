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
        assert format_name(" cool < file > name ") == " cool file name"

    def test_format_name_ends_without_dots(self):
        # A title that ends with "..." before the extension.
        assert (
            format_name("S01E02 Cat's in the Bag....mkv")
            == "S01E02 Cat's in the Bag.mkv"
        )
        # An empty episode title leaves a space before the extension.
        assert format_name("Severance S01E01 .mkv") == "Severance S01E01.mkv"
        # A folder: Windows refuses a dot at the end.
        assert format_name("Season 1 - The Beginning...") == "Season 1 - The Beginning"
        # The dots inside the name and of a language stay.
        assert format_name("Dune (2021).fr.srt") == "Dune (2021).fr.srt"
        assert format_name("Mr. Robot S01E01 eps1.0_hellofriend.mov") == (
            "Mr. Robot S01E01 eps1.0_hellofriend.mov"
        )

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


def test_fill_format_leaves_missing_values_out():
    from sok.core.utils import fill_format

    assert fill_format("{author} - {title} ({year})", {"title": "Dune"}) == "Dune"
    assert fill_format("{title} [{platform}]", {"title": "Doom"}) == "Doom"
    assert fill_format("{title} {unknown}", {"title": "Doom"}) == "Doom"
    assert fill_format("{title", {"title": "Doom"}) == ""
