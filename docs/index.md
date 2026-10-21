---
title: S.O.K developer documentation
description:
  How S.O.K is built, how to run it from source and how to contribute.
---

S.O.K (Storage Organisation Kit) is a desktop app that identifies media files
with online databases, then renames and moves them into a library that works
with Plex, Jellyfin and Kodi. It handles movies, TV shows, music, books and
games, on Windows, macOS and Linux.

This documentation is for people who work on the code. To use the app, see the
[user guide](https://sokfromsokteam.vercel.app/guide).

## Where to start

- **[Set up a development environment](/getting-started/setup/)**: clone the
  repository, install the dependencies and run the app from source.
- **[First steps with the code](/getting-started/first-steps/)**: search a
  database from Python, the way the app does.
- **[Architecture](/architecture/overview/)**: the layers of the app and how a
  search reaches an online database.
- **[Contributing](/contributing/)**: branches, commit messages, checks and pull
  requests.
- **[S.O.K Server](/specification/server/)**: the specification of the Docker
  version with a web interface, agreed before writing it.
- **API reference** (at the bottom of the sidebar): every module, class and
  function, generated from the docstrings.
- **[Changelog](https://github.com/SOKTeam/S.O.K/blob/main/CHANGELOG.md)**: what
  changed in each version.

## At a glance

|              |                                                             |
| ------------ | ----------------------------------------------------------- |
| Language     | Python 3.13                                                 |
| Interface    | PySide6 (Qt 6), built in code, no `.ui` files at run time   |
| Network      | `aiohttp`, one event loop per background worker             |
| Packaging    | Nuitka: Windows installer, macOS disk image, Linux AppImage |
| Dependencies | `uv` and `pyproject.toml`                                   |
| License      | [MIT](https://github.com/SOKTeam/S.O.K/blob/main/LICENSE)   |
