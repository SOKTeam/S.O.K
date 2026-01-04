# Quick Start

This guide will help you get started with S.O.K development.

## Basic Usage

### Using the Media Manager

The `UniversalMediaManager` is the central component for handling all media operations:

```python
import asyncio
from sok.core.media_manager import get_media_manager

async def main():
    manager = get_media_manager()

    # Search for a movie
    results = await manager.search("Inception", media_type="video")
    print(results)

    # Get movie details
    if results:
        details = await manager.get_details(results[0]["id"], media_type="video")
        print(details)

asyncio.run(main())
```

### Working with APIs Directly

You can also use individual APIs directly:

```python
import asyncio
from sok.apis.video.tmdb_api import TMDBApi

async def main():
    api = TMDBApi(api_key="your_api_key")

    async with api:
        results = await api.search("Inception", content_type=ContentType.MOVIE)
        print(results)

asyncio.run(main())
```

## Project Structure

```
src/sok/
├── __init__.py           # Package initialization
├── main.py               # Application entry point
├── core/                 # Core functionality
│   ├── interfaces.py     # Abstract interfaces
│   ├── media_manager.py  # Universal media manager
│   ├── exceptions.py     # Custom exceptions
│   └── utils.py          # Utility functions
├── apis/                 # External API integrations
│   ├── base_api.py       # Base API class
│   ├── video/            # Video APIs (TMDB, TVDB, IMDB)
│   ├── music/            # Music APIs (Spotify, Last.fm)
│   ├── books/            # Book APIs (Google Books)
│   └── games/            # Game APIs (IGDB, RAWG)
├── media/                # Media representations
│   ├── base_media.py     # Base media class
│   ├── video/            # Video media classes
│   ├── music/            # Music media classes
│   ├── books/            # Book media classes
│   └── games/            # Game media classes
├── file_operations/      # File system operations
│   ├── base_operations.py
│   └── ...
├── config/               # Configuration management
│   ├── config_manager.py
│   └── session_manager.py
└── ui/                   # User interface
    └── ...
```

## Key Concepts

### Media Types

S.O.K supports four main media types defined in `MediaType` enum:

- `VIDEO` - Movies, TV series, documentaries
- `MUSIC` - Albums, tracks, artists
- `BOOK` - Books, ebooks, audiobooks, comics
- `GAME` - Video games, DLCs

### Content Types

Each media type has specific content types defined in `ContentType` enum:

```python
from sok.core.interfaces import MediaType, ContentType

# Video content types
ContentType.MOVIE
ContentType.TV_SERIES
ContentType.EPISODE
ContentType.DOCUMENTARY

# Music content types
ContentType.ALBUM
ContentType.TRACK
ContentType.ARTIST

# Book content types
ContentType.BOOK
ContentType.EBOOK
ContentType.AUDIOBOOK
ContentType.COMIC

# Game content types
ContentType.GAME
ContentType.DLC
```

### API Interface

All APIs implement the `MediaAPI` abstract interface:

```python
class MediaAPI(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        content_type: ContentType,
        **kwargs
    ) -> Dict[str, Any]:
        """Search for media items"""
        pass

    @abstractmethod
    async def get_details(
        self,
        item_id: str,
        content_type: ContentType,
        **kwargs
    ) -> Dict[str, Any]:
        """Get detailed information about a media item"""
        pass

    @abstractmethod
    async def get_related_items(
        self,
        item_id: str,
        content_type: ContentType,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Get related items (episodes, tracks, etc.)"""
        pass
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sok

# Run specific test file
pytest tests/unit/test_media_manager.py
```

## Code Quality

```bash
# Linting
ruff check src/

# Formatting
ruff format src/

# Type checking
mypy src/
```
