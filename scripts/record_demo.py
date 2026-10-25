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
"""
Record the data of the demo of S.O.K Server (web/src/demo/data.json).

The demo on the website runs the web interface without a server: it answers
from the answers of a real sok-server. This script makes them: it creates a
downloads folder of empty files in a temporary folder, starts sok-server on
it with the API keys of the environment (.env), lets the automatic sorting
rename a first part, renames a second part by hand, analyzes the rest, then
picks each candidate of each row to know its new names.

Usage: uv run --extra server python scripts/record_demo.py
Then: cd web && npm run build:demo (the demo is in web/dist-demo).
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "web" / "src" / "demo" / "data.json"
MEDIA_TYPES = ["movies", "tv", "music", "books", "games"]
MB = 1024**2

# Sorted by the automatic sorting, the evening before the visit.
AUTO_SORTED = {
    "Interstellar.2014.1080p.BluRay.x265-RARBG.mkv": 9800 * MB,
    "Parasite.2019.KOREAN.1080p.BluRay.H264.mkv": 4200 * MB,
    "Parasite.2019.KOREAN.1080p.BluRay.H264.en.srt": 90 * 1024,
    "The.Grand.Budapest.Hotel.2014.720p.WEB-DL.mp4": 2100 * MB,
    "Severance.S01.1080p.ATVP.WEB-DL/Severance.S01E01.Good.News.About.Hell.1080p.mkv": 1900
    * MB,
    "Severance.S01.1080p.ATVP.WEB-DL/Severance.S01E02.Half.Loop.1080p.mkv": 1850 * MB,
    "Severance.S01.1080p.ATVP.WEB-DL/Severance.S01E03.In.Perpetuity.1080p.mkv": 1800
    * MB,
}
# Renamed by hand, two days before.
RENAMED = {
    "Radiohead - OK Computer/01 - Airbag.flac": 28 * MB,
    "Radiohead - OK Computer/02 - Paranoid Android.flac": 42 * MB,
    "Radiohead - OK Computer/03 - Subterranean Homesick Alien.flac": 30 * MB,
    "Andy Weir - Project Hail Mary.epub": 3 * MB,
}
# Waiting in the downloads folder: the rows of the visit.
WAITING = {
    "Inception.2010.1080p.BluRay.x264-SPARKS.mkv": 8700 * MB,
    "The.Matrix.1999.REMASTERED.2160p.UHD.BluRay.x265.mkv": 24000 * MB,
    "The.Matrix.1999.REMASTERED.2160p.UHD.BluRay.x265.fr.srt": 85 * 1024,
    "Dune.Part.Two.2024.MULTI.1080p.WEB.H264.mkv": 6400 * MB,
    "Blade.Runner.2049.2017.1080p.BluRay.DTS.x264.mkv": 11200 * MB,
    "Le.Fabuleux.Destin.d.Amelie.Poulain.2001.FRENCH.1080p.BluRay.mkv": 7300 * MB,
    "Spirited.Away.2001.JAPANESE.1080p.BluRay.mkv": 5600 * MB,
    "Alien.mkv": 3900 * MB,
    "Qzxvr.Plmtk.2021.1080p.WEB.mkv": 2300 * MB,
    "Breaking.Bad.S01.1080p.BluRay.x264/Breaking.Bad.S01E01.Pilot.1080p.mkv": 2400 * MB,
    "Breaking.Bad.S01.1080p.BluRay.x264/Breaking.Bad.S01E02.Cats.in.the.Bag.1080p.mkv": 2300
    * MB,
    "Breaking.Bad.S01.1080p.BluRay.x264/Breaking.Bad.S01E03.And.the.Bags.in.the.River.1080p.mkv": 2300
    * MB,
    "Dark.S01E01.MULTI.1080p.NF.WEB-DL.mkv": 2100 * MB,
    "Dark.S01E02.MULTI.1080p.NF.WEB-DL.mkv": 2000 * MB,
    "The.Office.S02E01.720p.WEB.mkv": 700 * MB,
    "The.Office.S02E02.720p.WEB.mkv": 700 * MB,
    "Daft Punk - Random Access Memories/01 - Give Life Back to Music.flac": 38 * MB,
    "Daft Punk - Random Access Memories/02 - The Game of Love.flac": 45 * MB,
    "Daft Punk - Random Access Memories/03 - Giorgio by Moroder.flac": 65 * MB,
    "Daft Punk - Random Access Memories/08 - Get Lucky.flac": 46 * MB,
    "Queen - Bohemian Rhapsody.mp3": 9 * MB,
    "Frank Herbert - Dune.epub": 2 * MB,
    "George Orwell - 1984.epub": 1 * MB,
    "Antoine de Saint-Exupery - Le Petit Prince.epub": 4 * MB,
    "The Legend of Zelda - Ocarina of Time (USA).z64": 32 * MB,
    "Super Mario World (USA).sfc": 1 * MB,
    "Pokemon - Emerald Version (USA).gba": 16 * MB,
    "Hollow Knight.iso": 8000 * MB,
    "VID_20240612_183001.mp4": 900 * MB,
}
# Arrives during the visit: the automatic sorting renames it.
ARRIVING = "Oppenheimer.2023.1080p.BluRay.x264-SPARKS.mkv"
ARRIVING_SIZE = 9100 * MB
# Searches the visitor can type on a row, by a file of the row.
SEARCHES = {
    "Le Petit Prince": "Antoine de Saint-Exupery - Le Petit Prince.epub",
    "The Office US": "The.Office.S02E01.720p.WEB.mkv",
}
HOUR = 3600
DAY = 24 * HOUR


class Server:
    """A sok-server on a free port of this machine, without login."""

    def __init__(self, config: Path) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        env = {
            **os.environ,
            "SOK_CONFIG_DIR": str(config),
            "SOK_AUTH": "none",
            "SOK_HOST": "127.0.0.1",
            "SOK_PORT": str(port),
        }
        self.process = subprocess.Popen(
            [sys.executable, "-m", "sok.server.app"],
            cwd=ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(60):
            try:
                self.call("/api/session")
                return
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.5)
        raise SystemExit("sok-server did not start")

    def call(self, path: str, method: str = "GET", body: object = None) -> object:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self.url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        with urllib.request.urlopen(request, timeout=120) as answer:
            return json.loads(answer.read() or "null")

    def until(self, test, what: str, seconds: int = 600) -> None:
        end = time.monotonic() + seconds
        while not test():
            if time.monotonic() > end:
                raise SystemExit(f"Timed out: {what}")
            time.sleep(2)

    def analyze(self) -> None:
        self.call("/api/scans", "POST")
        self.until(
            lambda: self.call("/api/scans/current")["scan"]["status"] != "running",
            "the analysis",
        )

    def rename(self, media_type: str) -> None:
        self.call("/api/renames", "POST", {"type": media_type})
        self.until(
            lambda: self.call("/api/renames/current")["rename"]["status"] != "running",
            "the rename",
        )

    def names(self, row: dict) -> dict:
        """The new names of the files of a row for each of its candidates."""
        picks = {}
        for index in range(len(row["candidates"])):
            picked = self.call(f"/api/rows/{row['id']}", "PATCH", {"selected": index})
            picks[index] = {
                "new_names": [f["new_name"] for f in picked["files"]],
                "episodes_found": picked["episodes_found"],
            }
        return picks

    def stop(self) -> None:
        self.process.terminate()
        self.process.wait(30)


def create(downloads: Path, files: dict) -> None:
    """Empty files of these sizes (sparse: they take no room)."""
    for name, size in files.items():
        path = downloads / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as file:
            file.truncate(size)


def record(server: Server, root: Path) -> dict:
    downloads = root / "downloads"
    media = root / "media"
    folders = {
        "sources": [downloads],
        "movies": [media / "Movies", media / "Movies 4K"],
        "tv": [media / "TV Shows"],
        "music": [media / "Music"],
        "books": [media / "Books"],
        "games": [media / "Games"],
    }
    for paths in folders.values():
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
    server.call(
        "/api/settings",
        "PATCH",
        {
            "folders": {k: [str(p) for p in v] for k, v in folders.items()},
            # Open Library needs no key.
            "settings": {"preferred_api_books": "openlibrary"},
        },
    )

    print("Automatic sorting (about 2 minutes)...")
    create(downloads, AUTO_SORTED)
    server.call(
        "/api/settings",
        "PATCH",
        {"settings": {"auto_sort": True, "auto_sort_minutes": 1}},
    )
    server.until(
        lambda: len(server.call("/api/history")["operations"]) >= 2,
        "the automatic sorting",
    )
    server.call("/api/settings", "PATCH", {"settings": {"auto_sort": False}})
    server.until(
        lambda: server.call("/api/scans/current")["scan"]["status"] != "running",
        "the end of the automatic sorting",
    )

    print("Renames by hand...")
    create(downloads, RENAMED)
    server.analyze()
    for media_type in ("music", "books"):
        for row in server.call(f"/api/rows?type={media_type}")["rows"]:
            if row["status"] != "ok" and row["candidates"]:
                server.call(f"/api/rows/{row['id']}", "PATCH", {"selected": 0})
        server.rename(media_type)

    print("The rows of the visit...")
    create(downloads, WAITING)
    server.analyze()
    data = {
        "settings": server.call("/api/settings"),
        "watch": server.call("/api/watch"),
        "summary": server.call("/api/scans/current"),
        "history": server.call("/api/history")["operations"],
        "processed": server.call("/api/processed")["files"],
        "rows": {t: server.call(f"/api/rows?type={t}")["rows"] for t in MEDIA_TYPES},
    }

    print("The candidates of each row...")
    rows = [row for t in MEDIA_TYPES for row in data["rows"][t]]
    data["names"] = {row["id"]: server.names(row) for row in rows}
    data["searches"] = []
    for query, file in SEARCHES.items():
        row = next(r for r in rows if any(f["name"] == file for f in r["files"]))
        found = server.call(f"/api/rows/{row['id']}/search", "POST", {"query": query})
        data["searches"].append(
            {
                "row": row["id"],
                "query": query,
                "found": found,
                "names": server.names(found),
            }
        )
    data["to_check_rows"] = []
    for item in data["summary"]["to_check"]:
        server.call(
            "/api/to-check", "POST", {"path": item["path"], "kind": item["kind"]}
        )
        row = next(
            r
            for r in server.call(f"/api/rows?type={item['media_type']}")["rows"]
            if any(f["path"] == item["path"] for f in r["files"])
        )
        data["to_check_rows"].append(
            {
                "path": item["path"],
                "kind": item["kind"],
                "row": row,
                "names": server.names(row),
            }
        )

    print("The file that arrives during the visit...")
    create(downloads, {ARRIVING: ARRIVING_SIZE})
    server.analyze()
    data["arriving"] = next(
        row
        for row in server.call("/api/rows?type=movies")["rows"]
        if row["files"][0]["name"] == ARRIVING
    )
    return data


def for_the_demo(data: dict) -> dict:
    """The dates in seconds before the visit, the settings of the demo."""
    settings = data["settings"]
    settings["settings"].update({"auto_sort": True, "auto_sort_minutes": 5})
    settings["notifications"]["discord"]["set"] = True
    settings["notifications"]["jellyfin"] = {"url": "http://jellyfin:8096", "set": True}

    # The automatic sorting of the evening before, the renames by hand of
    # two days before.
    ago = {"movies": 20 * HOUR, "tv": 20 * HOUR, "music": 2 * DAY + 3 * HOUR}
    for operation in data["history"]:
        operation["date"] = ago.get(operation["media_type"], 2 * DAY + 2 * HOUR)
    dates = {operation["id"]: operation["date"] for operation in data["history"]}
    for file in data["processed"]:
        file["date"] = dates[file["operation"]]
    renamed = sum(
        1
        for operation in data["history"]
        if operation["auto"]
        for file in operation["files"]
        if not file["follows"]
    )
    data["watch"] = {
        "enabled": True,
        "minutes": 5,
        "last_check": 2 * 60,
        "last_run": {"date": 20 * HOUR, "scan": 1, "renamed": renamed, "errors": []},
    }
    data["summary"]["scan"].update({"started": 3 * 60, "finished": 3 * 60 - 6})
    sizes = {**AUTO_SORTED, **RENAMED, **WAITING, ARRIVING: ARRIVING_SIZE}
    data["sizes"] = {f"/downloads/{name}": size for name, size in sizes.items()}
    return data


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        # The real path: the server writes resolved paths (/private/var on macOS).
        temp_dir = Path(temp).resolve()
        root = temp_dir / "root"
        server = Server(temp_dir / "config")
        try:
            data = record(server, root)
        finally:
            server.stop()
        # /tmp/.../root/downloads is /downloads in the demo, as in a container.
        text = json.dumps(for_the_demo(data), ensure_ascii=False).replace(str(root), "")
        shutil.rmtree(root, ignore_errors=True)
    if temp in text or str(temp_dir) in text:
        raise SystemExit("A path of this machine is left in the data")
    data = json.loads(text)
    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    count = sum(len(rows) for rows in data["rows"].values())
    print(f"{OUTPUT.relative_to(ROOT)}: {count} rows")


if __name__ == "__main__":
    main()
