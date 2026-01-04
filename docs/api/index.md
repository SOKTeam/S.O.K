# API Reference

This section contains the complete API reference for S.O.K, auto-generated from
Python docstrings.

## Modules

### Core

The core module contains the fundamental interfaces and managers:

- [**Interfaces**](core/interfaces.md) - Abstract base classes defining the contracts
- [**Media Manager**](core/media_manager.md) - Central orchestrator for all media
operations
- [**Exceptions**](core/exceptions.md) - Custom exception hierarchy
- [**Utils**](core/utils.md) - Utility functions

### APIs

External service integrations:

- [**Base API**](apis/base_api.md) - Common HTTP client functionality
- [**Video APIs**](apis/video.md) - TMDB, TVDB, IMDB
- [**Music APIs**](apis/music.md) - Spotify, Last.fm, Deezer, MusicBrainz
- [**Books APIs**](apis/books.md) - Google Books, OpenLibrary
- [**Games APIs**](apis/games.md) - IGDB, RAWG

### Media

Data models for media items:

- [**Base Media**](media/base_media.md) - Common media attributes
- [**Video**](media/video.md) - Movie, TVSeries, Episode
- [**Music**](media/music.md) - Album, Track, Artist
- [**Books**](media/books.md) - Book, Ebook, Audiobook
- [**Games**](media/games.md) - Game, DLC

### File Operations

File system operations:

- [**Base Operations**](file_operations/base_operations.md) - Common operations
- [**Video Operations**](file_operations/video_operations.md) - Video file handling
- [**Music Operations**](file_operations/music_operations.md) - Audio file handling
- [**Book Operations**](file_operations/book_operations.md) - Book file handling
- [**Game Operations**](file_operations/game_operations.md) - Game file handling

### Configuration

Settings and session management:

- [**Config Manager**](config/config_manager.md) - Application settings
- [**Session Manager**](config/session_manager.md) - API keys and tokens
- [**API Registry**](config/api_registry.md) - Service discovery
