# S.O.K Developer Documentation

Welcome to the **S.O.K (Storage Organisation Kit)** developer documentation.
This documentation is auto-generated from Python docstrings and provides
comprehensive API reference for developers working with the S.O.K codebase.

## What is S.O.K?

S.O.K is a universal media manager designed to organize, rename, and tag your
media collections including:

- **Movies & TV Series** - Integration with TMDB, TVDB, IMDB
- **Music** - Integration with Last.fm, Spotify, Deezer, MusicBrainz
- **Books** - Integration with Google Books, OpenLibrary
- **Games** - Integration with IGDB, RAWG

## Quick Links

<div class="grid cards" markdown>

- :material-rocket-launch: **[Getting Started](getting-started/installation.md)**

    Install S.O.K and get up and running quickly

- :material-sitemap: **[Architecture](architecture/overview.md)**

    Understand the project architecture and design patterns

- :material-api: **[API Reference](api/index.md)**

    Complete API documentation auto-generated from source

- :material-handshake: **[Contributing](contributing.md)**

    Learn how to contribute to the project

</div>

## Project Overview

```
sok/
├── core/           # Core interfaces, managers, and utilities
├── apis/           # External API integrations (TMDB, Spotify, etc.)
├── media/          # Media item representations
├── file_operations/ # File system operations
├── config/         # Configuration management
└── ui/             # User interface (PySide6)
```

## Key Features

- **Modular Architecture**: Clean separation between APIs, media types, and operations
- **Async Support**: Built on `aiohttp` for efficient API calls
- **Extensible**: Easy to add new media types and API integrations
- **Type-Safe**: Full type annotations with Python 3.13+

## Requirements

- Python 3.13+
- PySide6 for the GUI
- aiohttp for async HTTP requests

## License

S.O.K is licensed under the MIT License. See the
[LICENSE](https://github.com/SOKTeam/S.O.K/blob/main/LICENSE) file for details.
