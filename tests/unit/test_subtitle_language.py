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

from sok.file_operations.subtitle_language import (
    dialogue,
    flags_from_name,
    language_from_name,
    language_from_text,
)

LINES = {
    "fr": [
        "Je ne sais pas ce qui s'est passé hier soir.",
        "Tu aurais dû m'appeler avant de partir.",
        "Nous devons quitter la ville avant la tombée de la nuit.",
        "Il fait froid ici, ferme la fenêtre s'il te plaît.",
        "Où est-ce que tu as mis les clés de la voiture ?",
        "Je crois qu'il nous ment depuis le début.",
        "Personne ne doit savoir que nous sommes ici.",
        "Elle m'a dit qu'elle reviendrait demain matin.",
        "C'est la dernière fois que je te fais confiance.",
        "On n'a plus beaucoup de temps, dépêche-toi.",
        "Pourquoi est-ce que tu ne m'as rien dit ?",
        "Le désert est plus dangereux que tu ne le penses.",
    ],
    "en": [
        "I don't know what happened last night.",
        "You should have called me before you left.",
        "We have to leave the city before it gets dark.",
        "It's cold in here, please close the window.",
        "Where did you put the car keys?",
        "I think he has been lying to us from the start.",
        "Nobody can know that we are here.",
        "She told me she would come back tomorrow morning.",
        "This is the last time I ever trust you.",
        "We don't have much time left, hurry up.",
        "Why didn't you tell me anything?",
        "The desert is more dangerous than you think.",
    ],
    "es": [
        "No sé lo que pasó anoche.",
        "Deberías haberme llamado antes de irte.",
        "Tenemos que salir de la ciudad antes de que oscurezca.",
        "Hace frío aquí, cierra la ventana por favor.",
        "¿Dónde pusiste las llaves del coche?",
        "Creo que nos ha estado mintiendo desde el principio.",
        "Nadie puede saber que estamos aquí.",
        "Me dijo que volvería mañana por la mañana.",
        "Es la última vez que confío en ti.",
        "No nos queda mucho tiempo, date prisa.",
        "¿Por qué no me dijiste nada?",
        "El desierto es más peligroso de lo que crees.",
    ],
    "de": [
        "Ich weiß nicht, was gestern Abend passiert ist.",
        "Du hättest mich anrufen sollen, bevor du gegangen bist.",
        "Wir müssen die Stadt verlassen, bevor es dunkel wird.",
        "Es ist kalt hier drin, mach bitte das Fenster zu.",
        "Wo hast du die Autoschlüssel hingelegt?",
        "Ich glaube, er hat uns von Anfang an belogen.",
        "Niemand darf wissen, dass wir hier sind.",
        "Sie hat mir gesagt, dass sie morgen früh zurückkommt.",
        "Das ist das letzte Mal, dass ich dir vertraue.",
        "Wir haben nicht mehr viel Zeit, beeil dich.",
        "Warum hast du mir nichts gesagt?",
        "Die Wüste ist gefährlicher, als du denkst.",
    ],
}


def srt(lines):
    """An SRT file of these lines, each one a cue with <i> tags now and then."""
    cues = []
    for number, line in enumerate(lines, start=1):
        text = f"<i>{line}</i>" if number % 4 == 0 else line
        cues.append(
            f"{number}\n00:0{number // 60}:{number % 60:02},000 --> "
            f"00:0{number // 60}:{number % 60:02},900\n{text}\n"
        )
    return "\n".join(cues)


def write_srt(path, language, repeat=3, encoding="utf-8"):
    path.write_text(srt(LINES[language] * repeat), encoding=encoding)
    return path


@pytest.mark.parametrize(
    "name, language",
    [
        (".fr", "fr"),
        (".FRE.forced", "fr"),
        ("2_English", "en"),
        ("English [SDH]", "en"),
        ("Movie.VOSTFR", "fr"),
        ("Portuguese (Brazil)", "pt-BR"),
        ("Portuguese", "pt"),
        ("Brazilian", "pt-BR"),
        (".forced", None),
        (".hi", None),
        ("", None),
        ("3", None),
    ],
)
def test_the_language_is_read_from_the_name(name, language):
    assert language_from_name(name) == language


def test_flags_are_read_from_the_name():
    assert flags_from_name("4_English_SDH") == ["sdh"]
    assert flags_from_name("English (Forced) CC") == ["forced", "cc"]
    assert flags_from_name("2_English") == []


@pytest.mark.parametrize("language", ["fr", "en", "es", "de"])
def test_the_language_is_guessed_from_the_text(tmp_path, language):
    path = write_srt(tmp_path / "Movie.srt", language)

    assert language_from_text(path) == language


def test_a_windows_1252_file_is_read(tmp_path):
    path = write_srt(tmp_path / "Movie.srt", "fr", encoding="cp1252")

    assert language_from_text(path) == "fr"


def test_a_utf16_file_is_read(tmp_path):
    path = write_srt(tmp_path / "Movie.srt", "de", encoding="utf-16")

    assert language_from_text(path) == "de"


def test_a_short_subtitle_gets_no_language(tmp_path):
    path = write_srt(tmp_path / "Movie.srt", "fr", repeat=1)

    assert language_from_text(path) is None


def test_mixed_languages_get_no_language(tmp_path):
    lines = LINES["fr"] * 2 + LINES["en"] * 2
    (tmp_path / "Movie.srt").write_text(srt(lines))

    assert language_from_text(tmp_path / "Movie.srt") is None


def test_an_old_cyrillic_code_page_is_not_guessed(tmp_path):
    line = "Я не знаю, что случилось вчера вечером, и никто не знает."
    (tmp_path / "Movie.srt").write_text(srt([line] * 40), encoding="cp1251")

    assert language_from_text(tmp_path / "Movie.srt") is None


def test_the_language_of_a_vobsub_comes_from_its_idx(tmp_path):
    (tmp_path / "Movie.idx").write_text("# VobSub index file\nid: fr, index: 0\n")
    (tmp_path / "Movie.sub").write_bytes(b"\x00\x00\x01\xba" * 100)

    assert language_from_text(tmp_path / "Movie.idx") == "fr"
    assert language_from_text(tmp_path / "Movie.sub") is None


def test_an_idx_with_two_languages_gets_none(tmp_path):
    (tmp_path / "Movie.idx").write_text("id: fr, index: 0\nid: en, index: 1\n")

    assert language_from_text(tmp_path / "Movie.idx") is None


def test_the_dialogue_of_an_ass_file():
    text = (
        "[Script Info]\nTitle: Dune\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
        "Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,{\\an8}Bonjour, "
        "Paul.\\NTu viens ?\n"
    )

    assert dialogue(text, ".ass") == ["Bonjour, Paul. Tu viens ?"]


def test_the_dialogue_of_a_vtt_file():
    text = "WEBVTT\n\nNOTE made by hand\n\n00:01.000 --> 00:02.000\n<b>Hello</b>\n"

    assert dialogue(text, ".vtt") == ["Hello"]
