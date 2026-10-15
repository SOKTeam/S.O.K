---
title: First steps with the code
description:
  Search an online database from Python, directly or through the media manager
  the app uses.
---

These examples run from the repository root with `uv run python example.py`.
They use Deezer, which needs no API key.

## Call an API directly

Every database has its own class in `sok.apis`. They are asynchronous: use them
inside `async with` so their HTTP session is closed at the end.

```python title="example.py"
import asyncio

from sok.apis.music.deezer_api import DeezerApi
from sok.core.interfaces import ContentType


async def main():
    async with DeezerApi() as api:
        response = await api.search("Locket", ContentType.ALBUM)
        for album in response["results"][:3]:
            print(album["title"], "-", album["artist"])


asyncio.run(main())
```

```text
locket - Madison Beer
Locket - Crumb
Locket - Audrey Nuna
```

`search()` returns a dictionary whose `results` key holds the matches, with the
fields of that service. The constructor arguments differ from one API to
another: `TMDBApi(access_token)`, `TVDBApi(api_key)`,
`SpotifyApi(client_id, client_secret)`… See the API reference.

## Go through the media manager

The app does not pick an API itself. It asks the media manager, which creates
every API that has a key and selects the one chosen in _Settings_ for each media
type.

```python title="example.py"
import asyncio

from sok.core.interfaces import ContentType, MediaType
from sok.core.media_manager import get_media_manager


async def main():
    manager = get_media_manager()
    api = manager.get_current_api(MediaType.MUSIC)
    try:
        response = await manager.search("Locket", ContentType.ALBUM)
        album = response["results"][0]
        details = await manager.get_details(str(album["id"]), ContentType.ALBUM)
        print(details["title"], "-", len(details["tracks"]), "tracks")
    finally:
        await api.close()


asyncio.run(main())
```

The manager passes every response through an adapter
(`sok.core.adapters.media_adapters`), so the app gets the same fields whatever
the service. `get_media_manager()` always returns the same instance. It reads
the settings and the keys of your environment (see
[Set up a development environment](/getting-started/setup/)), so the API it uses
for music depends on your _Preferred API_ setting. APIs without a key are
skipped with a warning in the log.

## Media and content types

`MediaType` says which part of the app a search belongs to. `ContentType` says
what is searched:

| `MediaType` | `ContentType` values                           |
| ----------- | ---------------------------------------------- |
| `VIDEO`     | `MOVIE`, `TV_SERIES`, `EPISODE`, `DOCUMENTARY` |
| `MUSIC`     | `ALBUM`, `TRACK`, `ARTIST`, `PLAYLIST`         |
| `BOOK`      | `BOOK`, `EBOOK`, `AUDIOBOOK`, `COMIC`          |
| `GAME`      | `GAME`, `DLC`                                  |

Both are defined in `sok.core.interfaces`.
