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
"""Put a video in an MKV file while renaming it, without losing quality.

S.O.K Server can convert the MP4, M4V, MOV and TS videos it renames (the
convert_to_mkv setting). Only the container changes ("remux"): mkvmerge, of
MKVToolNix, copies the image, the sound and the subtitles as they are, in
about the time of a copy. It is a new file, so never with hard links: a
hard link would leave the torrent file the old one and take twice the room.

The MKV is written next to its destination under a temporary name, checked
(the same tracks of each kind, the same duration), then put in place. Only
then does a move delete the original; a copy keeps it. mkvmerge gives the
duration of an MKV only: the original's is read by mutagen (MP4, M4V, MOV)
or from the timestamps of its first and last packets (TS); a move whose
original has no duration that can be read is refused. A conversion that
fails or is not right leaves the original untouched and raises RemuxError.
AVI files are not converted: their sound often goes out of sync.
"""

import json
import logging
import os
import shutil
import subprocess
import uuid
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from sok.core.history import LINK, MOVE, current_journal

logger = logging.getLogger(__name__)

__all__ = [
    "CONVERTIBLE_EXTENSIONS",
    "MKV",
    "RemuxError",
    "convertible",
    "mkvmerge_path",
    "mkv_name",
    "convert_to_mkv",
]

# The videos converted; AVI is left out (sound out of sync).
CONVERTIBLE_EXTENSIONS = (".mp4", ".m4v", ".mov", ".ts")
MKV = ".mkv"

# mkvmerge: 0 done, 1 done with warnings, 2 failed.
_WARNINGS = 1
# The duration of the MKV may differ from the original's by this much.
DURATION_TOLERANCE_NS = 2_000_000_000
# Below this share of the original's size, the MKV lost something.
MIN_SIZE_RATIO = 0.5


class RemuxError(OSError):
    """A video could not be converted to MKV; the original is untouched."""


def mkvmerge_path() -> Optional[str]:
    """The mkvmerge program, or None when MKVToolNix is not installed.

    The SOK_MKVMERGE environment variable can give its path.
    """
    configured = os.environ.get("SOK_MKVMERGE", "").strip()
    if configured:
        return configured if os.path.isfile(configured) else None
    return shutil.which("mkvmerge")


def convertible(path: str) -> bool:
    """Whether a video is of a format converted to MKV."""
    return os.path.splitext(path)[1].lower() in CONVERTIBLE_EXTENSIONS


def mkv_name(filename: str) -> str:
    """The name of a video once converted: .mkv for the formats converted."""
    stem, extension = os.path.splitext(filename)
    return f"{stem}{MKV}" if extension.lower() in CONVERTIBLE_EXTENSIONS else filename


def _identify(program: str, path: str) -> Dict[str, Any]:
    """What mkvmerge reads of a file: its container and its tracks."""
    try:
        result = subprocess.run(
            [program, "--identification-format", "json", "--identify", path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        info = json.loads(result.stdout)
    except (OSError, ValueError) as exc:
        raise RemuxError(f"MKV conversion failed: cannot read {path}: {exc}") from exc
    if not isinstance(info, dict):
        raise RemuxError(f"MKV conversion failed: cannot read {path}")
    return info


def _tracks(info: Dict[str, Any]) -> Counter:
    """The number of tracks of each kind: video, audio, subtitles."""
    return Counter(track.get("type") for track in info.get("tracks") or [])


def _duration(info: Dict[str, Any]) -> Optional[int]:
    """The duration of a file in nanoseconds, when mkvmerge gives it (an MKV)."""
    duration = ((info.get("container") or {}).get("properties") or {}).get("duration")
    return duration if isinstance(duration, int) and duration > 0 else None


# MPEG-TS: packets of 188 bytes (192 with a timecode before), timestamps at
# 90 kHz on 33 bits.
TS_SYNC = 0x47
TS_PACKET_SIZES = (188, 192)
TS_CLOCK = 90_000
TS_WRAP = 1 << 33
# The bytes read at the start and at the end of a TS for its timestamps.
TS_SCAN = 4 * 1024 * 1024


def _ts_layout(data: bytes) -> Optional[Tuple[int, int]]:
    """(size of a packet, first byte of a packet) of a TS, or None."""
    for size in TS_PACKET_SIZES:
        sync = size - 188
        for start in range(min(size, len(data))):
            if all(
                start + sync + n * size < len(data)
                and data[start + sync + n * size] == TS_SYNC
                for n in range(5)
            ):
                return size, start
    return None


def _ts_timestamps(data: bytes, size: int, start: int) -> Dict[int, List[int]]:
    """The PTS of the PES packets of each video or audio stream, in order."""
    found: Dict[int, List[int]] = {}
    sync = size - 188
    for at in range(start, len(data) - size + 1, size):
        packet = data[at + sync : at + sync + 188]
        # A packet that starts a PES packet, with a payload.
        if packet[0] != TS_SYNC or not packet[1] & 0x40:
            continue
        control = (packet[3] >> 4) & 0x3
        if control not in (1, 3):
            continue
        offset = 4 + (1 + packet[4] if control == 3 else 0)
        pes = packet[offset:]
        # Video (0xE0-0xEF) or audio (0xC0-0xDF), with a PTS.
        if len(pes) < 14 or pes[:3] != b"\x00\x00\x01" or not 0xC0 <= pes[3] <= 0xEF:
            continue
        if not pes[7] & 0x80:
            continue
        b = pes[9:14]
        pts = (
            ((b[0] >> 1) & 0x07) << 30
            | b[1] << 22
            | (b[2] >> 1) << 15
            | b[3] << 7
            | b[4] >> 1
        )
        pid = ((packet[1] & 0x1F) << 8) | packet[2]
        found.setdefault(pid, []).append(pts)
    return found


def _ts_duration(path: str) -> Optional[int]:
    """The duration of a TS in nanoseconds: from the first to the last PTS of
    the stream that lasts longest, or None when they cannot be read."""
    with open(path, "rb") as file:
        head = file.read(TS_SCAN)
        file.seek(max(0, os.path.getsize(path) - TS_SCAN))
        tail = file.read(TS_SCAN)
    head_layout, tail_layout = _ts_layout(head), _ts_layout(tail)
    if head_layout is None or tail_layout is None:
        return None
    first = _ts_timestamps(head, *head_layout)
    last = _ts_timestamps(tail, *tail_layout)
    spans = [
        (last[pid][-1] - stamps[0]) % TS_WRAP
        for pid, stamps in first.items()
        if last.get(pid)
    ]
    if not spans or max(spans) <= 0:
        return None
    return max(spans) * 1_000_000_000 // TS_CLOCK


def source_duration(path: str) -> Optional[int]:
    """The duration of a video to convert in nanoseconds, or None."""
    try:
        if path.lower().endswith(".ts"):
            return _ts_duration(path)
        from mutagen.mp4 import MP4

        length = getattr(MP4(path).info, "length", 0)
    except Exception:  # noqa: BLE001 - a file that cannot be read
        return None
    return int(length * 1_000_000_000) if length and length > 0 else None


def _readable(source: str, info: Dict[str, Any]) -> None:
    """Raises RemuxError when mkvmerge cannot convert the source."""
    container = info.get("container") or {}
    if not container.get("recognized") or not container.get("supported"):
        raise RemuxError(
            f"MKV conversion failed: {os.path.basename(source)} is not a video "
            "mkvmerge can read"
        )
    if not _tracks(info).get("video"):
        raise RemuxError(
            f"MKV conversion failed: {os.path.basename(source)} has no video track"
        )


def _check(
    source: str,
    before: Dict[str, Any],
    partial: str,
    after: Dict[str, Any],
    mode: str,
) -> None:
    """Raises RemuxError when the MKV is not the same video as the source.

    Without a duration of the source, a copy is checked on the rest; a move,
    which deletes the original, is refused.
    """
    container = after.get("container") or {}
    if container.get("type") != "Matroska":
        raise RemuxError("MKV conversion failed: the new file is not an MKV")
    if _tracks(before) != _tracks(after):
        raise RemuxError(
            "MKV conversion failed: the new file does not have the same tracks"
        )
    first, last = source_duration(source), _duration(after)
    if first is None and mode == MOVE:
        raise RemuxError(
            "MKV conversion failed: the duration of the original cannot be read"
        )
    if first is not None and (
        last is None or abs(first - last) > DURATION_TOLERANCE_NS
    ):
        raise RemuxError(
            "MKV conversion failed: the new file does not have the same duration"
        )
    if os.path.getsize(partial) < os.path.getsize(source) * MIN_SIZE_RATIO:
        raise RemuxError("MKV conversion failed: the new file is too small")


def convert_to_mkv(
    source: str,
    destination: str,
    backup: bool = False,
    follows: Optional[str] = None,
    mode: str = MOVE,
) -> Optional[str]:
    """Convert a video to an MKV at its destination, like move_file moves it.

    Args:
        source: The video, of a format of CONVERTIBLE_EXTENSIONS.
        destination: The new path of the video, ending with .mkv.
        backup: Whether to keep a file already at the destination as
            '<destination>.backup'.
        follows: New path of the file this one goes with.
        mode: MOVE deletes the original once the MKV is checked; COPY keeps
            it. LINK is refused: the MKV is a new file.

    Returns:
        Path of the created backup, or None if no backup was made.

    Raises:
        RemuxError: mkvmerge is missing, fails, or makes a file that is not
            right. The original and the destination are left as they were.
    """
    if mode == LINK:
        raise ValueError("A hard link cannot be converted to MKV")
    program = mkvmerge_path()
    if program is None:
        raise RemuxError(
            "MKV conversion failed: mkvmerge (MKVToolNix) is not installed"
        )

    before = _identify(program, source)
    _readable(source, before)

    # Written next to the destination, then put in place once checked.
    partial = f"{destination}.sok-{uuid.uuid4().hex[:8]}"
    try:
        result = subprocess.run(
            [program, "--quiet", "--output", partial, source],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode > _WARNINGS or not os.path.exists(partial):
            message = (result.stdout or result.stderr).strip().splitlines()
            raise RemuxError(
                "MKV conversion failed: "
                + (
                    message[-1]
                    if message
                    else f"mkvmerge stopped ({result.returncode})"
                )
            )
        if result.returncode == _WARNINGS:
            logger.warning(
                "mkvmerge warnings for %s: %s", source, result.stdout.strip()
            )
        _check(source, before, partial, _identify(program, partial), mode)
    except BaseException:
        if os.path.exists(partial):
            os.remove(partial)
        raise

    backup_path = None
    try:
        if backup and os.path.exists(destination):
            backup_path = f"{destination}.backup"
            os.replace(destination, backup_path)
        os.replace(partial, destination)
    except OSError:
        if os.path.exists(partial):
            os.remove(partial)
        if backup_path:
            os.replace(backup_path, destination)
        raise

    if mode == MOVE:
        try:
            os.remove(source)
        except OSError as exc:
            # The MKV is in place: the original only takes room.
            logger.warning("Original kept after conversion %s: %s", source, exc)

    journal = current_journal()
    if journal:
        journal.moved(
            source, destination, backup_path, follows, mode=mode, converted=True
        )
    return backup_path
