# Project Structure

This document describes the complete project structure of S.O.K.

## Directory Layout

```
S.O.K/
├── src/                    # Source code
│   └── sok/               # Main package
├── tests/                  # Test suites
├── docs/                   # Documentation
├── scripts/                # Build and utility scripts
├── data/                   # Application data
├── tools/                  # Development tools
└── build/                  # Build outputs
```

## Source Code (`src/sok/`)

### Core Module (`core/`)

| File | Description |
| ------ | ------------- |
| `__init__.py` | Module exports |
| `interfaces.py` | Abstract interfaces (`MediaAPI`, `MediaItem`) |
| `media_manager.py` | `UniversalMediaManager` singleton |
| `exceptions.py` | Custom exception classes |
| `constants.py` | Service names and constants |
| `utils.py` | Utility functions |
| `security.py` | Credential encryption |
| `updater.py` | Application update logic |
| `adapters/` | Response adapters |

### APIs Module (`apis/`)

| Directory | Description |
| ----------- | ------------- |
| `base_api.py` | `BaseAPI` class with HTTP client |
| `video/` | TMDB, TVDB, IMDB integrations |
| `music/` | Spotify, Last.fm, Deezer, MusicBrainz |
| `books/` | Google Books, OpenLibrary |
| `games/` | IGDB, RAWG |
| `images/` | Fanart.tv |

### Media Module (`media/`)

| Directory | Description |
| ----------- | ------------- |
| `base_media.py` | `BaseMediaItem` class |
| `video/` | Movie, TVSeries, Episode classes |
| `music/` | Album, Track, Artist classes |
| `books/` | Book, Ebook, Audiobook classes |
| `games/` | Game, DLC classes |

### File Operations (`file_operations/`)

| File | Description |
| ------ | ------------- |
| `base_operations.py` | Common file operations |
| `video_operations.py` | Video file handling |
| `music_operations.py` | Audio file handling |
| `book_operations.py` | Book/PDF handling |
| `game_operations.py` | Game file handling |
| `mixins/` | Shared operation mixins |

### Configuration (`config/`)

| File | Description |
| ------ | ------------- |
| `config_manager.py` | Application settings |
| `session_manager.py` | API keys, OAuth tokens |
| `api_registry.py` | Service registration |
| `oauth_providers.py` | OAuth configuration |

### UI Module (`ui/`)

| Directory | Description |
| ----------- | ------------- |
| `main_window.py` | Main application window |
| `theme.py` | Theme and styling |
| `i18n.py` | Internationalization |
| `pages/` | Main view pages |
| `components/` | Reusable UI components |
| `dialogs/` | Dialog windows |
| `controllers/` | View controllers |
| `workers/` | Background workers |
| `factories/` | Widget factories |
| `designer/` | Qt Designer .ui files |
| `generated/` | Generated UI code |

## Tests (`tests/`)

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── functional/     # Functional tests
├── acceptance/     # Acceptance tests
├── performance/    # Performance tests
├── ui/             # UI tests
└── mock/           # Mock data and utilities
```

## Scripts (`scripts/`)

| Script | Purpose |
| -------- | --------- |
| `build_sok.py` | Build executable with Nuitka |
| `build_ui.py` | Compile Qt Designer files |
| `build_docs.py` | Build documentation |
| `installation.iss` | Inno Setup installer script |

## Configuration Files

| File | Purpose |
| ------ | --------- |
| `pyproject.toml` | Project metadata and dependencies |
| `mkdocs.yml` | Documentation configuration |
| `data/config.json` | Default application settings |

## Entry Points

### Application Entry

```python
# sok.main:main
def main():
    """Application entry point"""
    ...
```

### Package Entry

```python
# sok/__init__.py
from .__version__ import __version__
```
