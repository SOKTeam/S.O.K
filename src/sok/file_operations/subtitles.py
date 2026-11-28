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

When that name says no language, the language read from the text is
added when it is sure: Movie.srt in French becomes "Dune (2021).fr.srt".

The subtitles of a "Subs" folder next to the video go with it too:
Subs/2_English.srt for the only video of the folder, or
Subs/<video name>/2_English.srt for one episode of a pack. They are
named from the language of their name (or of their text) and their
flags, numbered when a language comes twice: "Dune (2021).en.srt",
"Dune (2021).en.2.srt", "Dune (2021).en.sdh.srt".
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from sok.core.history import MOVE
from sok.file_operations.base_operations import move_file
from sok.file_operations.subtitle_language import (
    flags_from_name,
    language_from_name,
    language_from_text,
)

logger = logging.getLogger(__name__)

SUBTITLE_EXTENSIONS = (".srt", ".ass", ".ssa", ".sub", ".idx", ".vtt")
SUBS_FOLDERS = ("subs", "subtitles")


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


def _listdir(folder: Path) -> List[str]:
    try:
        return sorted(os.listdir(folder))
    except OSError:
        return []


def find_subs_folder(video: Path, video_extensions: Iterable[str]) -> List[Path]:
    """The subtitles of a video in a "Subs" folder next to it.

    Subs/<video name>/ holds the subtitles of that video (an episode of a
    pack). Files right in Subs/ belong to the video only when it is the
    only video of its folder (a movie).

    Returns:
        The subtitle files, in the order of their leading number
        ("2_English.srt" before "10_French.srt").
    """
    names = _listdir(video.parent)
    folder = next(
        (
            video.parent / name
            for name in names
            if name.casefold() in SUBS_FOLDERS and (video.parent / name).is_dir()
        ),
        None,
    )
    if folder is None:
        return []
    inside = _listdir(folder)
    own = next(
        (
            folder / name
            for name in inside
            if name.casefold() == video.stem.casefold() and (folder / name).is_dir()
        ),
        None,
    )
    if own is not None:
        files = [own / name for name in _listdir(own)]
    else:
        video_extensions = tuple(ext.lower() for ext in video_extensions)
        # The video itself may already be gone: it moves before them.
        others = [
            name
            for name in names
            if name.lower().endswith(video_extensions) and name != video.name
        ]
        if others:
            return []
        files = [folder / name for name in inside]
    files = [
        path
        for path in files
        if path.name.casefold().endswith(SUBTITLE_EXTENSIONS) and path.is_file()
    ]

    def order(path: Path) -> Tuple[float, str]:
        number = re.match(r"\d+", path.name)
        return (int(number.group()) if number else float("inf"), path.name.casefold())

    return sorted(files, key=order)


def _pairs(files: List[Tuple[Path, str]]) -> List[List[Tuple[Path, str]]]:
    """Group (file, base) pairs: a VobSub .idx goes with the .sub of its base.

    The base is the name without the extension; two files of one group
    keep one base in their new names.
    """
    groups: List[List[Tuple[Path, str]]] = []
    for path, base in files:
        extension = path.suffix.lower()
        if extension in (".idx", ".sub"):
            partner = ".sub" if extension == ".idx" else ".idx"
            group = next(
                (
                    g
                    for g in groups
                    if len(g) == 1
                    and g[0][1] == base
                    and g[0][0].suffix.lower() == partner
                ),
                None,
            )
            if group is not None:
                group.append((path, base))
                continue
        groups.append([(path, base)])
    return groups


def _language_of(group: List[Tuple[Path, str]]) -> Optional[str]:
    """The language of a group read from its files (the .idx first)."""
    for path, _ in sorted(group, key=lambda item: item[0].suffix.lower() != ".idx"):
        language = language_from_text(path)
        if language:
            return language
    return None


def plan_subtitles(
    video: Path, new_video: str, video_extensions: Iterable[str]
) -> List[Tuple[str, str]]:
    """Where the subtitles of a video go when it goes to new_video.

    Returns:
        (source, target) pairs of paths; two targets never collide.
    """
    new_stem = os.path.splitext(new_video)[0]
    plan: List[Tuple[str, str]] = []
    claimed: Set[str] = set()

    def claim(group: List[Tuple[Path, str]], base: str) -> None:
        for path, _ in group:
            target = new_stem + base + path.suffix
            plan.append((str(path), target))
            claimed.add(target.casefold())

    def free(group: List[Tuple[Path, str]], base: str) -> bool:
        return all(
            (new_stem + base + path.suffix).casefold() not in claimed
            for path, _ in group
        )

    # Next to the video: the base is what follows the video's name.
    beside = [
        (path, suffix[: -len(path.suffix)] if path.suffix else suffix)
        for path, suffix in find_subtitles(video, video_extensions)
    ]
    guessed = []
    for group in _pairs(beside):
        base = group[0][1]
        if language_from_name(base):
            claim(group, base)
        else:
            guessed.append(group)
    for group in guessed:
        base = group[0][1]
        language = _language_of(group)
        if language and free(group, f".{language}{base}"):
            claim(group, f".{language}{base}")
        else:
            claim(group, base)

    # In a Subs folder: the name is made from the language and the flags.
    inside = [(path, path.stem) for path in find_subs_folder(video, video_extensions)]
    for group in _pairs(inside):
        name = group[0][1]
        language = language_from_name(name) or _language_of(group)
        parts = ([language] if language else []) + flags_from_name(name)
        base = "".join(f".{part}" for part in parts)
        number = 2
        numbered = base
        while not free(group, numbered):
            numbered = f"{base}.{number}"
            number += 1
        claim(group, numbered)
    return plan


def move_subtitles(
    video: Path,
    new_video: str,
    video_extensions: Iterable[str],
    skip_duplicates: bool = False,
    backup: bool = False,
    mode: str = MOVE,
    dry_run: bool = False,
) -> Dict[str, List[Dict[str, Any]]]:
    """Move the subtitles of a video next to its new place, under its new name.

    Those beside the video and those of its Subs folder go, with their
    language added when the name lacks it and the text says it surely
    (see plan_subtitles). The history records each subtitle as following the video, so undoing
    the video puts them back too.

    Args:
        video: Where the video was.
        new_video: Where the video went.
        video_extensions: Extensions of the videos.
        skip_duplicates: Leave a subtitle in place when its new name exists.
        backup: Keep a replaced subtitle as '<name>.backup'.
        mode: MOVE, LINK or COPY, like the video.
        dry_run: Only say where they would go.

    Returns:
        "moved", "skipped" and "errors" lists, like the organize reports.
    """
    report: Dict[str, List[Dict[str, Any]]] = {
        "moved": [],
        "skipped": [],
        "errors": [],
    }
    for source, target in plan_subtitles(video, new_video, video_extensions):
        if source == target:
            continue
        if skip_duplicates and os.path.exists(target):
            report["skipped"].append({"file": source, "reason": "File already exists"})
            continue
        if not dry_run:
            try:
                move_file(source, target, backup=backup, follows=new_video, mode=mode)
            except OSError as exc:
                logger.warning("Subtitle move failed for %s: %s", source, exc)
                report["errors"].append({"file": source, "error": str(exc)})
                continue
        report["moved"].append({"from": source, "to": target})
    return report
