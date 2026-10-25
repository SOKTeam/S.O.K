---
title: Writing tests
description:
  Where tests go, and how to test without the network, without your own settings
  and without blocking the interface.
---

The tests use [pytest](https://docs.pytest.org) with
[pytest-qt](https://pytest-qt.readthedocs.io) for the interface and
[pytest-asyncio](https://pytest-asyncio.readthedocs.io) for coroutines. They are
installed with the `dev` extra.

```sh
uv run pytest tests/                       # everything
uv run pytest tests/unit/test_batch.py     # one file
uv run pytest tests/ -k "ready and not book"   # tests whose name matches
```

The interface tests need a display. Without one (a server, a container, an SSH
session), set `QT_QPA_PLATFORM=offscreen`, as the CI does. The CI runs the tests
on Linux and macOS for each pull request to `develop` or `main`.

## Where a test goes

| Folder                       | For                                                                       |
| ---------------------------- | ------------------------------------------------------------------------- |
| `unit/`                      | One function or class: name parsing, batch matching, adapters, API errors |
| `integration/`               | Several modules together, on real files in a temporary folder             |
| `functional/`, `acceptance/` | A complete scenario, from the files to the organized library              |
| `ui/`                        | Widgets, pages and workers, with pytest-qt                                |
| `server/`                    | The API of S.O.K Server, with FastAPI's `TestClient`                      |
| `mock/`                      | An API class against a recorded response                                  |
| `performance/`               | Timing of file operations                                                 |

Name the file `test_<what>.py` and write tests as sentences:
`test_a_wrong_key_is_an_authentication_error`. Each file builds what it needs,
so a test reads on its own. The only shared fixture is in `tests/conftest.py`:
`rename_history` gives every test a rename history of its own in `tmp_path`, so
no test ever writes to yours. Take it as an argument to read what a rename
recorded.

## Tests of the web interface

The web interface of S.O.K Server has its own tests, with
[Vitest](https://vitest.dev), next to the code they test
(`web/src/lib/*.test.ts`): the helpers that need no browser. The server of
the demo has its own (`web/src/demo/server.test.ts`): renames, undo, searches
and the automatic sorting, with fake timers. `svelte-check` checks the types
of the pages.

```sh
cd web
npm test        # Vitest
npm run check   # svelte-check
```

The pages are checked in a real browser before each pull request (see
[The web project](/server/overview/#the-web-project)).

## Never call a real service

Tests must pass without a network and without keys. Fake one level, the lowest
that the test does not need:

- **The HTTP session**, to test an API class and `BaseAPI` (statuses, JSON
  errors). `tests/unit/test_api_http_errors.py` replaces `_ensure_session` by a
  coroutine that returns a fake session:

  ```python
  api = GoogleBooksApi()

  async def fake_session():
      return FakeSession(FakeResponse(429, {"error": {"message": "Quota"}}))

  api._ensure_session = fake_session
  with pytest.raises(APIRateLimitError):
      asyncio.run(api._make_request("volumes", {"q": "Dune"}))
  ```

- **`_make_request`**, to test how an API class reads a response
  (`tests/unit/test_rawg_titles.py`):

  ```python
  async def fake_request(endpoint, params):
      return {"results": [{"id": 1, "name": "Halo (PC)"}]}

  api._make_request = fake_request
  ```

- **The media manager**, to test what uses it (the batch engine, the workers):
  an object with an `async def search(self, query, content_type, **kwargs)`
  method is enough. `tests/unit/test_game_batch.py` gives `BatchMatcher` a
  manager that raises an error.

## Never use your own settings

From source, `get_config_manager()` reads and writes `data/config.json` in the
repository: the settings of the app you run, with your formats, folders and
keys. A test that uses it gives a result that depends on them. Replace it in the
module under test with a small object:

```python
class FakeConfig:
    def __init__(self, **values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def test_tracks_follow_the_music_format(monkeypatch):
    cfg = FakeConfig(music_format="{artist}/{title}")
    monkeypatch.setattr(music_operations, "get_config_manager", lambda: cfg)
    ...
```

Patch the name where it is used (`music_operations.get_config_manager`), not
where it is defined: each module imported it under its own name.

The language of the interface also comes from your settings: a test that
compares a text built with `tr()` passes in English and fails in French.
Compare file names, numbers or the result of the same `tr()` call instead.

## Files

Use the `tmp_path` fixture of pytest for every file a test creates or moves. An
empty file is enough for most tests (`path.write_text("")`): S.O.K reads names,
not contents. Audio tags are the exception: replace
`MusicFileOperations.read_metadata` with a function that returns the tags
(`tests/unit/test_track_batch.py`).

## Coroutines

A synchronous test can run a coroutine with `asyncio.run()`, as most tests do.
An `async def` test needs the marker:

```python
@pytest.mark.asyncio
async def test_search_movie():
    result = await api.search("Fight Club", ContentType.MOVIE)
```

## The interface

pytest-qt gives the `qtbot` fixture. Register each widget you create, so that it
is closed after the test:

```python
def test_only_ready_rows_are_renamed(qtbot):
    table = MediaBatchTable([".mkv"])
    qtbot.addWidget(table)
    ...
```

Workers run in another thread, so their results arrive later. Wait for them
instead of sleeping:

```python
with qtbot.waitSignal(worker.error, timeout=2000) as signal:
    worker.run()
assert "quota" in signal.args[0]

qtbot.waitUntil(lambda: len(calls) == 2)
```

`tests/ui/test_worker_runner.py` checks that the callbacks of `WorkerRunner` run
in the GUI thread: widgets must never be created anywhere else.

Code that depends on the system is tested on every system: fake the system
instead of skipping the test. `tests/ui/test_request_attention.py` sets
`sok.ui.platform.IS_MACOS`, and `tests/ui/test_mac_volumes.py` replaces
`QStorageInfo.mountedVolumes` with a list of fake disks.

## Before pushing

Run the [checks](/contributing/#checks) of the CI. They lint and format `src/`
only; keep the tests clean too with `uv run ruff check tests`.
