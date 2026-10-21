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
"""Input patterns: how the user's file names are built.

A pattern uses the variables of the name formats, such as
"{artist} - {year} - {album} - {track} - {title}". The parsers of the file
operations try the patterns of the settings before their own rules, so a
naming scheme S.O.K does not know can still be read.

In a pattern, spaces, dots and underscores are the same separator, and the
separators around a dash are optional. {year} takes four digits; {season},
{episode}, {track}, {disc} and {series_number} take a number; the other
variables take text. {ignore} skips a part of the name, as many times as
needed.
"""

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# One key per kind of name: the episodes and the movies are both videos but
# are read differently.
EPISODE = "episode"
MOVIE = "movie"
MUSIC = "music"
BOOK = "book"
GAME = "game"

IGNORE = "ignore"

# Variables a pattern of each kind accepts, and the one it needs.
VARIABLES: Dict[str, List[str]] = {
    EPISODE: ["title", "season", "episode", "episode_title", "year"],
    MOVIE: ["title", "year"],
    MUSIC: ["artist", "album", "disc", "track", "title", "year"],
    BOOK: ["author", "title", "series", "series_number", "year"],
    GAME: ["title", "platform", "region", "year"],
}
REQUIRED: Dict[str, str] = {
    EPISODE: "episode",
    MOVIE: "title",
    MUSIC: "title",
    BOOK: "title",
    GAME: "title",
}

# What the parsers read without any pattern, written as patterns. Shown in
# the settings; the parsers themselves use their own rules.
BUILTIN: Dict[str, List[str]] = {
    EPISODE: [
        "{title} S{season}E{episode}",
        "{title} {season}x{episode}",
        "{title} Season {season} Episode {episode}",
        "{title} Saison {season} Episode {episode}",
        "{title} {season}.{episode}",
        "{title} Ep {episode}",
    ],
    MOVIE: ["{title} ({year})", "{title} {year} {ignore}"],
    MUSIC: [
        "{artist} - {album} - {track} - {title}",
        "CD{disc} {track} {title}",
        "{track} - {title}",
        "{track}. {title}",
        "Track {track} {title}",
    ],
    BOOK: [
        "{author} - [{series} {series_number}] - {title}",
        "{author} - {title} ({year})",
        "{author} - {title}",
        "{title} - {author}",
    ],
    GAME: ["[{platform}] {title} ({region})", "{title} ({region}) [{ignore}]"],
}

NUMBERS = {"season", "episode", "disc", "track", "series_number"}

_FIELD = re.compile(r"\{([^{}]*)\}")
_SEP = r"[\s._]+"
_DASH = r"[\s._]*\-[\s._]*"


class PatternError(ValueError):
    """A pattern that cannot be used.

    Attributes:
        code: What is wrong: "braces", "unknown", "twice" or "required".
        name: The variable concerned, if any.
    """

    def __init__(self, code: str, name: str = "") -> None:
        super().__init__(f"{code}: {name}" if name else code)
        self.code = code
        self.name = name


@dataclass
class PatternMatch:
    """A pattern that matched a file name, and the values it read."""

    pattern: str
    values: Dict[str, Any]


def _literal(text: str) -> str:
    """Regex for the text between two variables."""
    if "{" in text or "}" in text:
        raise PatternError("braces")
    if text.strip(" ._") == "-":
        return _DASH
    pieces = []
    for piece in re.split(r"([\s._]+)", text):
        if piece:
            pieces.append(_SEP if not piece.strip(" ._") else re.escape(piece))
    regex = "".join(pieces)
    return regex.replace(_SEP + r"\-", _DASH).replace(r"\-" + _SEP, _DASH)


def compile_pattern(kind: str, pattern: str) -> "re.Pattern[str]":
    """Turn a pattern into a regex that matches a whole file name.

    Args:
        kind: EPISODE, MOVIE, MUSIC, BOOK or GAME.
        pattern: The pattern, such as "{title} ({year})".

    Returns:
        The compiled regex, case-insensitive, with one group per variable.

    Raises:
        PatternError: The pattern is not valid for that kind.
    """
    allowed = VARIABLES[kind]
    # (text between the previous variable and this one, variable name)
    fields = []
    end = 0
    for field in _FIELD.finditer(pattern):
        fields.append((_literal(pattern[end : field.start()]), field.group(1).strip()))
        end = field.end()
    tail = _literal(pattern[end:])

    regex = []
    seen = set()
    for i, (before, name) in enumerate(fields):
        regex.append(before)
        next_name = fields[i + 1][1] if i + 1 < len(fields) else None
        if name == IGNORE:
            regex.append(r".*?")
            continue
        if name not in allowed:
            raise PatternError("unknown", name)
        if name in seen:
            raise PatternError("twice", name)
        seen.add(name)
        if name == "year":
            regex.append(r"(?P<year>(?:18|19|20)\d{2})")
        elif name in NUMBERS:
            # "{season}{episode}": "0105" is 1 and 5, "105" too.
            glued = i > 0 and not before and fields[i - 1][1] in NUMBERS
            digits = r"\d{2}" if glued else r"\d{1,3}"
            regex.append(rf"(?P<{name}>{digits})")
        elif next_name == "year":
            # The year is the last one: "Blade Runner 2049 (2017)".
            regex.append(rf"(?P<{name}>.+)")
        else:
            regex.append(rf"(?P<{name}>.+?)")
    regex.append(tail)
    if REQUIRED[kind] not in seen:
        raise PatternError("required", REQUIRED[kind])
    return re.compile(r"[\s._]*" + "".join(regex) + r"[\s._]*", re.IGNORECASE)


def check_pattern(kind: str, pattern: str) -> Optional[PatternError]:
    """Return what is wrong with a pattern, or None if it can be used."""
    try:
        compile_pattern(kind, pattern)
    except PatternError as error:
        return error
    return None


def _text(value: str) -> str:
    """Tidy a text value: "The.Office" → "The Office"."""
    if " " not in value.strip():
        value = re.sub(r"[._]+", " ", value)
    return value.strip(" ._-")


def match_name(kind: str, stem: str, patterns: List[str]) -> Optional[PatternMatch]:
    """Read a file name with the first pattern that matches it.

    Args:
        kind: EPISODE, MOVIE, MUSIC, BOOK or GAME.
        stem: The file name, without its extension.
        patterns: The patterns to try, in order. Invalid ones are skipped.

    Returns:
        The pattern and its values (numbers as int), or None.
    """
    for pattern in patterns:
        try:
            regex = compile_pattern(kind, pattern)
        except PatternError:
            continue
        found = regex.fullmatch(stem)
        if not found:
            continue
        values: Dict[str, Any] = {}
        for name, value in found.groupdict().items():
            if name == "year" or name in NUMBERS:
                values[name] = int(value)
            else:
                values[name] = _text(value)
        return PatternMatch(pattern, values)
    return None


def user_patterns(kind: str) -> List[str]:
    """Patterns of the settings for a kind of name."""
    from sok.config.config_manager import get_config_manager

    saved = get_config_manager().get("input_patterns", {})
    if not isinstance(saved, dict):
        return []
    patterns = saved.get(kind, [])
    return (
        [p for p in patterns if isinstance(p, str)]
        if isinstance(patterns, list)
        else []
    )


def match_user_pattern(kind: str, filename: str) -> Optional[PatternMatch]:
    """Read a file name with the patterns of the settings.

    Args:
        kind: EPISODE, MOVIE, MUSIC, BOOK or GAME.
        filename: The file name, with its extension.
    """
    patterns = user_patterns(kind)
    if not patterns:
        return None
    return match_name(kind, os.path.splitext(filename)[0], patterns)
