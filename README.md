<div align="center">

# S.O.K - Storage Organisation Kit

![S.O.K Logo](src/sok/resources/assets/logo.png)

**The ultimate assistant to tame your media library.**

![CI](https://img.shields.io/github/actions/workflow/status/SOKTeam/S.O.K/ci.yml?branch=main&label=CI&logo=github)
![Release](https://img.shields.io/github/actions/workflow/status/SOKTeam/S.O.K/release.yml?branch=main&label=Release&logo=github)
![Version](https://img.shields.io/github/v/release/SOKTeam/S.O.K)
![Python](https://img.shields.io/badge/python-3.13+-blue?logo=python)
![Code Coverage](https://img.shields.io/codecov/c/github/SOKTeam/S.O.K?logo=codecov)
![License](https://img.shields.io/badge/license-MIT-green)
![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)

[Features](#-features) • [Installation](#-quick-installation) • [Contribute](#-contribution)
</div>

---

## 👋 Why S.O.K?

Are you tired of folders named `New_Folder(2)`, files like
`DSC_0012.mp4`, or music albums without cover art?

**S.O.K** (Storage Organisation Kit) was born from a simple need: to end
digital chaos. It's a powerful universal manager designed to identify,
rename, and automatically organize your collections, whether they are movies,
TV series, music, books, or video games.
It doesn't just move files; it understands what they are thanks to
a multitude of specialized APIs.

---

## ✨ Features

### 🎬 Videos (Movies & TV Shows)

Transform a messy folder into a Kodi/Plex/Jellyfin-compatible library.

- **Precise identification** via TMDB, TVDB, and IMDb.
- **Smart renaming**: `breaking.bad.s01e01.720p.mkv` ➔
`Breaking Bad/Season 01/Breaking Bad - S01E01 - Pilot.mkv`.
- **Technical details**: Automatic detection of quality (4K, 1080p) and
codecs (x265, HEVC).

### 🎵 Music

Rediscover your audio library.

- **Complete tagging**: Automatic addition of ID3 metadata (Artist, Album, Year).
- **Multiple sources**: Spotify, Last.fm, Deezer, MusicBrainz.
- **Organization**: Structure by `Artist/Album/Track - Title`.

### 📚 Books & Comics

Your digital library, finally sorted.

- **E-book support**: Management of EPUB and PDF files.
- **Metadata**: Retrieval of info via Google Books, OpenLibrary, and Goodreads.
- **Classification**: Sort by Author or by Series.

### 🎮 Video Games

For ROM and ISO collectors.

- **Retrogaming**: Organization by console and platform.
- **Info**: Data from IGDB, RAWG, and Steam.

---

## 🚀 Quick Installation

We recommend using [uv](https://github.com/astral-sh/uv) for
an ultra-fast experience, but `pip` works just as well.

### Option A: The modern way (recommended)

```bash
# 1. Clone the project
git clone https://github.com/SOKTeam/S.O.K
cd S.O.K

# 2. Install and sync (creates venv automatically)
uv sync

# 3. Launch the application
uv run sok
```

### Option B: The classic way (pip)

```bash
# 1. Create the virtual environment
python3.13 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 2. Install dependencies
pip install -e .

# 3. Launch
python src/sok/main.py
```

### 🔑 API Configuration

For the magic to happen, S.O.K needs access keys. Create a `.env` file
at the root:

```bash
cp .env.example .env
```

Fill it with your keys (TMDB, Spotify, etc.). *Don't panic, the software
works in limited mode without all keys.*

---

## 💻 For Developers

S.O.K is designed to be modular. You can use its building blocks in your
own scripts.

**Code architecture:**

- `src/sok/core`: The core reactor (interfaces, security).
- `src/sok/apis`: Connectors to the outside world (TMDB, Spotify...).
- `src/sok/file_operations`: Renaming and moving logic.

**Library usage example:**

```python
import asyncio
from sok.media.video import Series

async def main():
    # Instantiate a series
    show = Series("Arcane")

    # Fetch info
    print("Searching for episodes...")
    episodes = await show.get_episodes()

    # Start organization
    await show.rename_files("./downloads/arcane_s2")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🛠️ Roadmap

We are actively working on version 2.x. Here's what's coming:

- [x] Architecture overhaul (Modular & Async)
- [x] Full Video support (TMDB/TVDB)
- [x] Modern graphical interface (PySide6)
- [ ] **Coming soon**: Full Comics support (ComicVine)
- [ ] **Coming soon**: "Service" mode (Background scanning)
- [ ] **Idea**: Plugin for automatic subtitle download

---

## 🤝 Contribution

Open Source is at the heart of this project. Have an idea? Found a bug?

1. Take a look at the [Issues](https://github.com/S-O-K-Team/sok/issues).
2. Fork the project.
3. Create your branch (`git checkout -b feature/SuperFeature`).
4. Submit your Pull Request!

Check out our [Contribution Guide](CONTRIBUTING.md) for technical details.

---

<div align="center">

**Made with ❤️ by the S.O.K Team**

MIT License © 2026

</div>
