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
server           S.O.K Server: FastAPI application, database, login (no Qt)
 │
core             media manager, interfaces, adapters, exceptions, updater
 │
 ├── apis             one class per online database
 ├── media            data models (movie, episode, album, book, game…)
 ├── file_operations  scanning, renaming and moving files
 └── config           settings, API keys and sessions, service registry
```

Only `sok.ui` and `sok.main` import Qt. PySide6 and pypresence are in the
`desktop` extra, so the layers below run without them, as S.O.K Server does;
`tests/unit/test_core_without_qt.py` imports them with the desktop dependencies
blocked.

## Layers

### Interface (`sok.ui`)

Built in code with PySide6; no Qt Designer file is loaded at run time.

- `main_window.py`: the window, the sidebar and the page stack. On Windows and
  Linux the window is frameless with its own title bar; on macOS it keeps the
  native title bar.
- `pages/`: home, TV shows (`organize_page.py`), music (an Albums and a Tracks
  tab), the batch pages (`batch_page.py` and its movies, books, games and tracks
  subclasses), settings and the history of renames (`history_page.py`).
- `components/`: reusable widgets (search results, preview, settings sections…).
- `controllers/`: logic shared by the pages (source scanning, preview, window
  chrome, `WorkerRunner`).
- `workers/`: background tasks (search, details, organize, folder creation,
  batch search and rename, detection of dropped files, undo of a rename).
- `dialogs/`: the update dialog.
- `errors.py`: the messages shown for API errors.
- `factories/`: builds `sok.media` objects from API responses, so the pages do
  not create them themselves.
- `theme.py`, `platform.py`, `i18n.py`: colors and fonts, per-system behavior,
  translations.
- `message_box.py`: message boxes, shown as sheets on macOS.
- `macos_menu.py`: the native macOS menu bar.

### Core (`sok.core`)

- `media_manager.py`: `UniversalMediaManager`, the single entry point to the
  online databases. It creates the APIs that have a key, keeps the one selected
  for each media type and normalizes their responses.
- `interfaces.py`: `MediaAPI`, the contract every API implements, and the
  `MediaType` and `ContentType` enums.
- `adapters/media_adapters/`: one adapter per kind of content (movie, TV, music,
  book, game) that turns a service response into the fields the app uses.
- `batch.py`: the batch engine. It reads file names, searches many files at once
  and decides which ones are Ready (see
  [The path of a rename](/architecture/organizing/)). No Qt dependency.
- `name_patterns.py`: the input patterns of the settings, which the file
  operations try before their own rules to read a file name. No Qt dependency.
- `history.py`: the rename history and its undo (see
  [Rename history](/architecture/organizing/#rename-history)). No Qt dependency.
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
  media type, with shared mixins, `organize.py` for the batches and
  `detection.py`, which sorts the files dropped on the home page by type.
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

Renaming follows a similar path, through the file operations instead of the
APIs: see [The path of a rename](/architecture/organizing/).

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
