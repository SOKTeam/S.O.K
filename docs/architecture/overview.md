---
title: Architecture overview
description:
  The layers of S.O.K and the path of a search, from the interface to an online
  database and back.
---

S.O.K is one Python package, `sok`, split into layers. Each layer only calls the
layers below it.

```text
ui               PySide6 interface: window, pages, components, workers
 │
core             media manager, interfaces, adapters, exceptions, updater
 │
 ├── apis             one class per online database
 ├── media            data models (movie, episode, album, book, game…)
 ├── file_operations  scanning, renaming and moving files
 └── config           settings, API keys and sessions, service registry
```

## Layers

### Interface (`sok.ui`)

Built in code with PySide6; no Qt Designer file is loaded at run time.

- `main_window.py`: the window, the sidebar and the page stack. On Windows and
  Linux the window is frameless with its own title bar; on macOS it keeps the
  native title bar.
- `pages/`: home, organize (TV shows, music, books, games), movies and settings.
- `components/`: reusable widgets (search results, preview, settings sections…).
- `controllers/`: logic shared by the pages (source scanning, preview, window
  chrome, `WorkerRunner`).
- `workers/`: background tasks (search, details, organize, folder scan).
- `theme.py`, `platform.py`, `i18n.py`: colors and fonts, per-system behavior,
  translations.

### Core (`sok.core`)

- `media_manager.py`: `UniversalMediaManager`, the single entry point to the
  online databases. It creates the APIs that have a key, keeps the one selected
  for each media type and normalizes their responses.
- `interfaces.py`: `MediaAPI`, the contract every API implements, and the
  `MediaType` and `ContentType` enums.
- `adapters/media_adapters/`: one adapter per kind of content (movie, TV, music,
  book, game) that turns a service response into the fields the app uses.
- `exceptions.py`: the exception hierarchy (see below).
- `updater.py`: checks GitHub releases and installs updates.
- `desktop_entry.py`: adds S.O.K to the Linux applications menu.

### APIs (`sok.apis`)

One class per service, all derived from `BaseAPI` (`base_api.py`), which holds
the HTTP session and the error handling:

| Folder    | Services                              |
| --------- | ------------------------------------- |
| `video/`  | TMDB, TVDB, OMDb (`imdb_api.py`)      |
| `music/`  | Last.fm, Spotify, Deezer, MusicBrainz |
| `books/`  | Google Books, Open Library            |
| `games/`  | IGDB, RAWG                            |
| `images/` | Fanart.tv                             |

### Media, file operations and configuration

- `sok.media`: data classes for each kind of item (`Movie`, `Episode`, `Album`,
  `Track`, `Book`, `Game`…), all derived from `BaseMedia`.
- `sok.file_operations`: reads names (season and episode numbers, years), builds
  the new names from the user's formats and moves the files. One module per
  media type, with shared mixins.
- `sok.config`: `config_manager.py` (settings and folders), `session_manager.py`
  (keys and tokens), `api_registry.py` (the list of services, their media type
  and how they authenticate).

## The path of a search

1. The user types in a search field. The page starts a `SearchWorker` with a
   `WorkerRunner`, which moves it to a `QThread`.
2. The worker creates its own asyncio event loop and calls
   `get_media_manager().search(query, content_type)`.
3. The manager sends the query to the API selected for that media type.
4. The API calls the service with `aiohttp` and returns its response.
5. The manager passes it through the adapter of the content type.
6. The worker emits a Qt signal; the page shows the results in the GUI thread.

Each worker has its own event loop, so an API opens a new HTTP session when the
loop changes (`BaseAPI._ensure_session()`): a session can only be used on the
loop that created it.

:::caution
Widgets and `QPixmap` must only be created in the GUI thread. Workers
send plain data (dictionaries, bytes) through signals.
:::

## Choosing the API

`UniversalMediaManager` reads `api_registry.py` at startup. For each media type
it creates every service that has its key, then selects the one in the
`preferred_api_<type>` setting, or the first one available.
`set_current_api_for_media_type()` changes it while the app runs.

## Exceptions

All exceptions derive from `SOKBaseError` (`sok.core.exceptions`):

```text
SOKBaseError
├── APIError
│   ├── APIAuthenticationError
│   ├── APIConnectionError
│   ├── APINotFoundError
│   ├── APIRateLimitError
│   ├── APIResponseError
│   └── APITimeoutError
├── ConfigurationError
│   └── MissingConfigurationError
├── FileOperationError
│   ├── FileNotFoundError
│   └── FilePermissionError
└── MediaError
    ├── MediaNotFoundError
    └── UnsupportedMediaTypeError
```

`sok.core.exceptions.FileNotFoundError` is not the built-in one: import it
explicitly.
