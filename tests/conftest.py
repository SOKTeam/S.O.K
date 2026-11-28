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

from sok.core import history


@pytest.fixture(autouse=True)
def rename_history(tmp_path, monkeypatch):
    """A rename history of its own for each test, never the user's one."""
    store = history.HistoryStore(tmp_path / "history.json")
    monkeypatch.setattr(history, "_history", store)
    return store


class FakeMkvmerge:
    """mkvmerge of MKVToolNix without the program: subprocess.run of
    remux.py answers as it would. The MKV is a copy of the original.

    fail: the conversion stops with an error; tracks / duration: what the
    MKV made has (the original: a video and an audio track, 100 s);
    source_duration: what source_duration() reads of the original.
    """

    SOURCE_TRACKS = ["video", "audio"]
    DURATION = 100_000_000_000

    def __init__(self) -> None:
        self.fail = False
        self.tracks = list(self.SOURCE_TRACKS)
        self.duration = self.DURATION
        self.source_duration = self.DURATION
        self.outputs = set()
        self.conversions = []

    def run(self, args, **_kwargs):
        import shutil
        import subprocess

        if "--identify" in args:
            path = args[-1]
            if path in self.outputs:
                kind, tracks, duration = "Matroska", self.tracks, self.duration
            else:
                kind, tracks, duration = (
                    "QuickTime/MP4",
                    self.SOURCE_TRACKS,
                    self.DURATION,
                )
            info = {
                "container": {
                    "recognized": True,
                    "supported": True,
                    "type": kind,
                    "properties": {"duration": duration},
                },
                "tracks": [{"id": i, "type": t} for i, t in enumerate(tracks)],
            }
            import json

            return subprocess.CompletedProcess(args, 0, json.dumps(info), "")
        output = args[args.index("--output") + 1]
        source = args[-1]
        if self.fail:
            return subprocess.CompletedProcess(
                args, 2, "Error: The file could not be read.\n", ""
            )
        shutil.copyfile(source, output)
        self.outputs.add(output)
        self.conversions.append((source, output))
        return subprocess.CompletedProcess(args, 0, "", "")


@pytest.fixture
def fake_mkvmerge(monkeypatch, tmp_path):
    """mkvmerge installed, answering as FakeMkvmerge."""
    from sok.file_operations import remux

    fake = FakeMkvmerge()
    program = tmp_path / "mkvmerge"
    program.write_text("")
    monkeypatch.setenv("SOK_MKVMERGE", str(program))
    monkeypatch.setattr(remux.subprocess, "run", fake.run)
    monkeypatch.setattr(remux, "source_duration", lambda path: fake.source_duration)
    return fake
