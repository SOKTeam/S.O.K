---
title: Adding an API
description:
  Connect a new online database to S.O.K, from the API class to the key the
  release builds carry.
---

An API is a class that implements `MediaAPI` (`sok.core.interfaces`), usually
through `BaseAPI`. The media manager then creates it at startup when its key is
available.

## 1. Write the class

Create a module in the folder of its media type, for example
`src/sok/apis/games/example_api.py`:

```python
from typing import Any, Dict, List

from sok.apis.base_api import BaseAPI
from sok.core.interfaces import ContentType, MediaType


class ExampleApi(BaseAPI):
    """Example game database. Documentation: https://api.example.com/docs"""

    def __init__(self, api_key: str = ""):
        super().__init__(api_key, "https://api.example.com/v1/")

    @property
    def supported_media_types(self) -> List[MediaType]:
        return [MediaType.GAME]

    @property
    def supported_content_types(self) -> List[ContentType]:
        return [ContentType.GAME]

    async def search(
        self, query: str, content_type: ContentType, **kwargs: Any
    ) -> Dict[str, Any]:
        response = await self._make_request("games", {"q": query, "key": self.api_key})
        return {
            "results": [
                {"id": game["id"], "title": game["name"], "release_date": game.get("released")}
                for game in response.get("items", [])
            ]
        }

    async def get_details(
        self, item_id: str, content_type: ContentType, **kwargs: Any
    ) -> Dict[str, Any]:
        return await self._make_request(f"games/{item_id}", {"key": self.api_key})

    async def get_related_items(
        self, item_id: str, content_type: ContentType, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError("Example has no related items.")
```

`BaseAPI` gives you:

- `_make_request(endpoint, params, headers, method, data, json_data)`: sends the
  request with the shared `aiohttp` session and returns the decoded JSON. The
  endpoint is appended to the base URL.
- A session per event loop (`_ensure_session()`): background workers each run
  their own loop, and a session cannot be reused on another one.
- `async with` support and `close()`.

Raise the exceptions of `sok.core.exceptions` (`APIAuthenticationError`,
`APIRateLimitError`, `APINotFoundError`…) rather than generic ones: the media
manager and the workers handle `APIError` and its subclasses.

## 2. Return the fields the adapters expect

The media manager passes `search()` and `get_details()` results through the
adapter of the content type (`sok.core.adapters.media_adapters`). Look at the
adapter for your content type and at an existing API of the same media type,
then use the same keys (`id`, `title`, `release_date`, `overview`…): the
movie and TV adapters keep the overview for the results S.O.K Server shows. If a field has another
name in your service, rename it in your class rather than in the adapter.

## 3. Register the service

| File                               | What to add                                                                                                                                                                                                                                                   |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/sok/core/constants.py`        | `SERVICE_EXAMPLE = "example"`, its `CONFIG_KEY_` and `ENV_` names, the entries in `API_KEY_CONFIG` and `API_KEY_ENV`, and an `API_KEY_EXAMPLE = ""` line in the `Constants` class.                                                                            |
| `src/sok/config/api_registry.py`   | An `APIServiceConfig` entry: name, description, `media_type`, `auth_type`, `group` (`APIGroup.FREE` if it works without a key: the manager then creates it without arguments), `config_key`, `env_var`, `api_key_url`. The settings page lists it from there. |
| `src/sok/core/media_manager.py`    | The class in the `api_classes` dictionary. Services that need more than one key (like Spotify or IGDB) also need a branch where the instances are created.                                                                                                    |
| `src/sok/apis/key_check.py`        | A `Probe` in `PROBES` when the service takes a key: one light request that needs the key, for the "Test" button of S.O.K Server ([Testing a key](/server/overview/#testing-a-key)).                                                                           |
| `src/sok/config/config_manager.py` | The key in `SENSITIVE_FIELDS`, so it is saved encrypted.                                                                                                                                                                                                      |
| `.env.example`                     | The environment variable, with the URL where a key is obtained.                                                                                                                                                                                               |

The `Constants` line matters for the release builds: `scripts/build_sok.py` only
copies into the app the `.env` values that the `Constants` class declares,
encrypted.

## 4. Test it

Add tests that mock the HTTP responses (see `tests/mock/test_tmdb_mock.py` and
`tests/unit/test_api_session.py`), then try the service in the app: select it in
_Settings → API keys → Preferred API_ and run a search.
