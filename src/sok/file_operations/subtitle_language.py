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
"""The language of a subtitle file, from its name or from its text.

The name is read first: "fr", "fre", "French", "VOSTFR" and the like say
the language. When the name says nothing, the text is read and its
language guessed with langdetect, only when the guess is sure: enough
dialogue, a high probability, and both halves of the text agree. A
subtitle is never given a language S.O.K is unsure of.

The language is written as a two-letter code ("fr"), the form Kodi,
Jellyfin and Plex read.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

# Words of a subtitle name that say a language, folded to lower case.
_LANGUAGES: Dict[str, Iterable[str]] = {
    "ar": ("ar", "ara", "arabic"),
    "bg": ("bg", "bul", "bulgarian"),
    "ca": ("ca", "cat", "catalan"),
    "cs": ("cs", "cze", "ces", "czech"),
    "da": ("da", "dan", "danish"),
    "de": ("de", "ger", "deu", "german", "deutsch"),
    "el": ("el", "gre", "ell", "greek"),
    "en": ("en", "eng", "english"),
    "es": ("es", "spa", "spanish", "espanol", "castellano", "latino"),
    "et": ("et", "est", "estonian"),
    "fa": ("fa", "per", "fas", "persian", "farsi"),
    "fi": ("fi", "fin", "finnish"),
    "fr": ("fr", "fre", "fra", "french", "francais", "vostfr", "vfq", "vff"),
    "he": ("he", "heb", "hebrew"),
    "hr": ("hr", "hrv", "croatian"),
    "hu": ("hu", "hun", "hungarian"),
    "id": ("id", "ind", "indonesian"),
    "is": ("ice", "isl", "icelandic"),
    "it": ("it", "ita", "italian", "italiano"),
    "ja": ("ja", "jpn", "japanese"),
    "ko": ("ko", "kor", "korean"),
    "lt": ("lt", "lit", "lithuanian"),
    "lv": ("lv", "lav", "latvian"),
    "ms": ("ms", "may", "msa", "malay"),
    "nl": ("nl", "dut", "nld", "dutch"),
    "no": ("no", "nor", "nob", "norwegian"),
    "pl": ("pl", "pol", "polish", "polski"),
    "pt": ("pt", "por", "portuguese", "portugues"),
    "pt-BR": ("pt-br", "ptbr", "brazilian", "brazil"),
    "ro": ("ro", "rum", "ron", "romanian"),
    "ru": ("ru", "rus", "russian"),
    "sk": ("sk", "slo", "slk", "slovak"),
    "sl": ("sl", "slv", "slovenian"),
    "sr": ("sr", "srp", "serbian"),
    "sv": ("sv", "swe", "swedish"),
    "th": ("th", "tha", "thai"),
    "tr": ("tr", "tur", "turkish"),
    "uk": ("uk", "ukr", "ukrainian"),
    "vi": ("vi", "vie", "vietnamese"),
    "zh": ("zh", "chi", "zho", "chinese"),
}
WORD_LANGUAGES = {word: code for code, words in _LANGUAGES.items() for word in words}

# Words of a subtitle name that describe it, kept in the new name.
# "hi" is hearing impaired here, never Hindi.
FLAGS = ("forced", "sdh", "cc", "hi")

TEXT_EXTENSIONS = (".srt", ".ass", ".ssa", ".vtt", ".sub")

# A guess counts only with this much dialogue and this probability.
MIN_LINES = 30
MIN_LETTERS = 600
MIN_PROBABILITY = 0.95
# What is read of a file, and of its dialogue for the guess.
MAX_BYTES = 1024 * 1024
MAX_SAMPLE = 20000

_TIMING = re.compile(r"\d+:\d+[:.,]\d+.*-->")
_TAG = re.compile(r"<[^>]*>|\{[^}]*\}")
_WORDS = re.compile(r"[^\W_]+(?:-[^\W_]+)?")


def name_words(name: str) -> List[str]:
    """The words of a name, folded: "2_English [SDH]" → ["2", "english", "sdh"]."""
    return _WORDS.findall(name.casefold())


def language_from_name(name: str) -> Optional[str]:
    """The language a name says, or None ("Movie.fr.forced" → "fr").

    "Portuguese (Brazil)" is Brazilian Portuguese, not Portuguese.
    """
    found = [
        WORD_LANGUAGES[word] for word in name_words(name) if word in WORD_LANGUAGES
    ]
    if "pt-BR" in found:
        return "pt-BR"
    return found[0] if found else None


def flags_from_name(name: str) -> List[str]:
    """The flags of a name, in the order of FLAGS ("English SDH" → ["sdh"])."""
    words = set(name_words(name))
    return [flag for flag in FLAGS if flag in words]


def read_text(path: Path) -> Optional[str]:
    """The text of a subtitle file, or None when its encoding is unsure.

    UTF-8 and UTF-16 (with a byte order mark) are read as they are. Other
    files are read as Windows-1252 only when nearly all their letters are
    plain ASCII: a Cyrillic or Greek file in an old code page would come
    out as nonsense and get a wrong language.
    """
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_BYTES)
    except OSError:
        return None
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="ignore")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    high = sum(1 for byte in data if byte >= 0x80)
    letters = sum(1 for byte in data if 0x41 <= byte <= 0x7A)
    if letters and high / letters <= 0.05:
        return data.decode("cp1252", errors="ignore")
    return None


def dialogue(text: str, extension: str) -> List[str]:
    """The lines spoken in a subtitle, without numbers, timings or tags."""
    lines: List[str] = []
    is_ass = extension in (".ass", ".ssa")
    for raw in text.splitlines():
        line = raw.strip()
        if is_ass:
            if not line.startswith("Dialogue:"):
                continue
            parts = line.split(",", 9)
            line = parts[9] if len(parts) == 10 else ""
            line = line.replace("\\N", " ").replace("\\n", " ").replace("\\h", " ")
        if not line or line.isdigit() or line.startswith("WEBVTT"):
            continue
        if _TIMING.match(line) or line.startswith(("NOTE", "STYLE", "REGION")):
            continue
        line = _TAG.sub(" ", line).replace("|", " ").strip()
        if any(char.isalpha() for char in line):
            lines.append(line)
    return lines


def _best(text: str) -> Optional[tuple]:
    """(language, probability) of the likeliest language of a text."""
    try:
        from langdetect import DetectorFactory, detect_langs
        from langdetect.lang_detect_exception import LangDetectException
    except ImportError:
        logger.warning("langdetect is missing: subtitle languages are not guessed")
        return None
    # The same text always gives the same answer.
    DetectorFactory.seed = 0
    try:
        found = detect_langs(text)
    except LangDetectException:
        return None
    if not found:
        return None
    code = found[0].lang.split("-")[0]
    return code, found[0].prob


def guess_language(lines: List[str]) -> Optional[str]:
    """The language of some dialogue, only when the guess is sure."""
    letters = sum(sum(char.isalpha() for char in line) for line in lines)
    if len(lines) < MIN_LINES or letters < MIN_LETTERS:
        return None
    # Lines from the whole file, not only from its start.
    step = max(1, sum(len(line) + 1 for line in lines) // MAX_SAMPLE)
    sample = lines[::step]
    half = len(sample) // 2
    whole = _best(" ".join(sample))
    first = _best(" ".join(sample[:half]))
    second = _best(" ".join(sample[half:]))
    if not whole or not first or not second:
        return None
    if whole[1] < MIN_PROBABILITY or not whole[0] == first[0] == second[0]:
        return None
    return whole[0] if whole[0] in _LANGUAGES else None


def language_from_text(path: Path) -> Optional[str]:
    """The language of a subtitle file read from its content, or None.

    A VobSub .idx says it on its "id:" lines; a text subtitle is guessed
    from its dialogue. A picture subtitle (VobSub .sub) cannot be read.
    """
    extension = path.suffix.lower()
    if extension == ".idx":
        text = read_text(path) or ""
        ids = {
            match.group(1).casefold()
            for match in re.finditer(r"^id:\s*([A-Za-z]{2,3})\b", text, re.M)
        }
        if len(ids) == 1:
            return WORD_LANGUAGES.get(ids.pop())
        return None
    if extension not in TEXT_EXTENSIONS:
        return None
    content = read_text(path)
    if not content or (extension == ".sub" and "\x00" in content[:2048]):
        return None
    return guess_language(dialogue(content, extension))
