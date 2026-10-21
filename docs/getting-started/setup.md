---
title: Set up a development environment
description: Clone the repository, install the dependencies and run S.O.K from source.
---

## Requirements

- **Python 3.13** or later.
- **[uv](https://docs.astral.sh/uv/)**: installs the dependencies from `uv.lock`
  and runs the tools.
- **Git**.
- **Docker**, only to build the Linux AppImage or to preview this documentation.

## Install

```sh
git clone https://github.com/SOKTeam/S.O.K.git
cd S.O.K
uv sync --extra dev
```

`uv sync` creates `.venv/` and installs the exact versions from `uv.lock`. The
dependencies of the core need no Qt; the extras add the rest:

| Extra     | Contents                                                                              |
| --------- | ------------------------------------------------------------------------------------- |
| `desktop` | PySide6 and pypresence, for the desktop app                                           |
| `server`  | FastAPI and uvicorn, for S.O.K Server                                                 |
| `dev`     | `desktop`, `server`, pytest, pytest-qt, pytest-asyncio, ruff, mypy, ty, python-dotenv |
| `docs`    | griffe, which describes the package for the API reference                             |
| `build`   | `desktop`, Nuitka and the packaging tools                                             |

Combine them as needed, for example `uv sync --extra dev --extra docs`.

## API keys

Most databases need a key. Copy `.env.example` to `.env` at the repository root
and fill in the keys you have. Deezer, MusicBrainz and Open Library work without
one.

```sh
cp .env.example .env
```

`.env` is ignored by git. Never commit it.

## Run the app

```sh
uv run sok
```

When it runs from source, S.O.K keeps its files in the repository:

| File     | Location           |
| -------- | ------------------ |
| Settings | `data/config.json` |
| Log      | `logs/sok.log`     |

Both folders are ignored by git. Set `SOK_LOG_LEVEL=DEBUG` for a more detailed
log. Every setting and variable is listed in
[Settings and environment](/reference/settings/).

:::note
The installed app stores them elsewhere: next to the executable on Windows, in
`~/Library/Application Support/S.O.K` and `~/Library/Logs/S.O.K` on macOS, and
in the XDG folders (`~/.local/share/S.O.K`, `~/.local/state/S.O.K/logs`) on
Linux. `SOK_CONFIG_DIR` puts the settings, the history and the log in one folder
instead, such as a test folder.
:::

## Check your setup

These are the checks the CI runs on every pull request:

```sh
uv run ruff check src
uv run ruff format --check src
uv run python tools/verify_i18n.py
uv run mypy --install-types --non-interactive src/sok --ignore-missing-imports --no-strict-optional
uv run ty check src
uv run pytest tests/
```

The interface tests need a display. On a machine without one (a server, a
container), set `QT_QPA_PLATFORM=offscreen`.
