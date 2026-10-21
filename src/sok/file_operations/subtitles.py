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
"""Subtitles that follow their video.

A subtitle whose name starts with the name of a video goes with it:
Movie.srt, Movie.fr.srt and Movie.en.forced.srt follow Movie.mkv. It is
renamed like the video and keeps what follows the video's name, so
Movie.fr.srt becomes "Dune (2021).fr.srt" next to "Dune (2021).mkv".
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from sok.file_operations.base_operations import move_file

logger = logging.getLogger(__name__)

SUBTITLE_EXTENSIONS = (".srt", ".ass", ".ssa", ".sub", ".idx", ".vtt")


def find_subtitles(
    video: Path, video_extensions: Iterable[str]
) -> List[Tuple[Path, str]]:
    """The subtitles of a video, next to it.

    When two videos of the folder can claim a subtitle (Movie.mkv and
    Movie.Part2.mkv for Movie.Part2.srt), the longest name wins.

    Args:
        video: The video file.
        video_extensions: Extensions of the videos, to find the other ones.

    Returns:
        (subtitle, suffix) pairs; the suffix is what follows the video's
        name, such as ".fr.srt".
    """
    video_extensions = tuple(ext.lower() for ext in video_extensions)
    stem = video.stem.casefold()
    try:
        names = os.listdir(video.parent)
    except OSError:
        return []

    other_stems = [
        Path(name).stem.casefold()
        for name in names
        if name.lower().endswith(video_extensions) and name != video.name
    ]
    subtitles = []
    for name in sorted(names):
        folded = name.casefold()
        if not folded.endswith(SUBTITLE_EXTENSIONS) or not folded.startswith(
            stem + "."
        ):
            continue
        if any(
            len(other) > len(stem) and folded.startswith(other + ".")
            for other in other_stems
        ):
            continue
        subtitles.append((video.parent / name, name[len(video.stem) :]))
    return subtitles


def move_subtitles(
    video: Path,
    new_video: str,
    video_extensions: Iterable[str],
    skip_duplicates: bool = False,
    backup: bool = False,
    dry_run: bool = False,
) -> Dict[str, List[Dict[str, Any]]]:
    """Move the subtitles of a video next to its new place, under its new name.

    The history records each subtitle as following the video, so undoing
    the video puts them back too.

    Args:
        video: Where the video was.
        new_video: Where the video went.
        video_extensions: Extensions of the videos.
        skip_duplicates: Leave a subtitle in place when its new name exists.
        backup: Keep a replaced subtitle as '<name>.backup'.
        dry_run: Only say where they would go.

    Returns:
        "moved", "skipped" and "errors" lists, like the organize reports.
    """
    report: Dict[str, List[Dict[str, Any]]] = {
        "moved": [],
        "skipped": [],
        "errors": [],
    }
    new_stem = os.path.splitext(new_video)[0]
    for subtitle, suffix in find_subtitles(video, video_extensions):
        source = str(subtitle)
        target = new_stem + suffix
        if source == target:
            continue
        if skip_duplicates and os.path.exists(target):
            report["skipped"].append({"file": source, "reason": "File already exists"})
            continue
        if not dry_run:
            try:
                move_file(source, target, backup=backup, follows=new_video)
            except OSError as exc:
                logger.warning("Subtitle move failed for %s: %s", source, exc)
                report["errors"].append({"file": source, "error": str(exc)})
                continue
        report["moved"].append({"from": source, "to": target})
    return report
