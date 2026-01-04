# Media Module

The `sok.media` module contains data models representing different types of media
items.

## Overview

All media items inherit from a common base class that provides:

- Standard attributes (title, metadata, IDs)
- Formatted naming for files
- Folder structure generation

```mermaid
classDiagram
    class BaseMediaItem {
        +title: str
        +media_type: MediaType
        +content_type: ContentType
        +metadata: Dict
        +get_formatted_name() str
        +get_folder_structure() List[str]
    }

    class Movie {
        +year: int
        +director: str
        +tmdb_id: str
    }

    class Album {
        +artist: str
        +year: int
        +tracks: List[Track]
    }

    BaseMediaItem <|-- Movie
    BaseMediaItem <|-- Album
```

## Submodules

- [Base Media](base_media.md) - Common media attributes
- [Video](video.md) - Movie, TVSeries, Episode
- [Music](music.md) - Album, Track, Artist
- [Books](books.md) - Book, Ebook, Audiobook
- [Games](games.md) - Game, DLC
