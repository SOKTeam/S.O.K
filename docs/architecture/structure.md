---
title: Project structure
description: What each folder of the repository contains.
---

```text
S.O.K/
├── src/sok/          the application package
├── web/              the web interface of S.O.K Server (Svelte)
├── tests/            pytest suites
├── docs/             this documentation (Kiln), configured by docs.yml
├── scripts/          build, version and documentation scripts
├── tools/            development checks
├── packaging/        installer files for each system
├── .github/          CI, release and Linux build workflows
├── Dockerfile        the S.O.K Server image (with .dockerignore)
├── pyproject.toml    metadata, dependencies and tool settings
└── uv.lock           exact dependency versions
```

## `src/sok/`

| Path               | Contents                                                                                                                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `main.py`          | Entry point (`uv run sok`): logging, `QApplication`, main window                                                                                                                                             |
| `__version__.py`   | Version, kept in sync with `pyproject.toml`                                                                                                                                                                  |
| `core/`            | Media manager, interfaces, adapters, batch engine, input patterns, rename history, exceptions, constants, updater, Linux desktop entry                                                                       |
| `apis/`            | One module per online database, by media type (`video/`, `music/`, `books/`, `games/`, `images/`)                                                                                                            |
| `media/`           | Data classes: `Movie`, `Series`, `Episode`, `Album`, `Track`, `Artist`, `Playlist`, `Book`, `Ebook`, `Audiobook`, `Comic`, `Game`, `DLC`; `factory.py` builds them from search results (`create_media_item`) |
| `file_operations/` | Name parsing, renaming and moving, by media type, with shared mixins                                                                                                                                         |
| `config/`          | Settings and folders, keys and sessions, service registry, OAuth providers                                                                                                                                   |
| `server/`          | S.O.K Server, the FastAPI application (see [S.O.K Server](/server/overview/))                                                                                                                                |
| `ui/`              | The PySide6 interface (see [Architecture](/architecture/overview/#interface-sokui))                                                                                                                          |
| `resources/`       | Icons and logos (`assets/`), Inter font for Linux (`fonts/`), translations (`i18n/`)                                                                                                                         |

`ui/designer/` holds old Qt Designer mockups and `ui/generated/` is the empty
folder meant for the code generated from them. Neither is used by the app.

## `tests/`

| Folder                       | Contents                                                         |
| ---------------------------- | ---------------------------------------------------------------- |
| `unit/`                      | Functions and classes in isolation                               |
| `integration/`               | Several modules together                                         |
| `functional/`, `acceptance/` | Complete scenarios: renaming, organizing videos, music and books |
| `ui/`                        | Widgets and pages, with pytest-qt                                |
| `server/`                    | The API of S.O.K Server, with FastAPI's `TestClient`             |
| `mock/`                      | Tests against recorded API responses                             |
| `performance/`               | Timing of file operations                                        |

## `scripts/` and `tools/`

| File                           | Purpose                                                                                          |
| ------------------------------ | ------------------------------------------------------------------------------------------------ |
| `scripts/build_sok.py`         | Compiles the app with Nuitka (see [Building the app](/guides/building/))                         |
| `scripts/bump_version.py`      | Writes the version everywhere; `--check` fails if a file is out of sync                          |
| `scripts/build_docs.py`        | Builds or previews this documentation (see [Writing this documentation](/guides/documentation/)) |
| `scripts/make_macos_assets.py` | Draws the macOS icon and disk image background                                                   |
| `scripts/check.py`             | Runs ruff, mypy, ty and pytest in a row                                                          |
| `tools/verify_i18n.py`         | Compares the `tr()` keys of the code and the `t()` keys of `web/src` with the translation files  |

## `packaging/`

| File                            | Purpose                                                |
| ------------------------------- | ------------------------------------------------------ |
| `windows/installation.iss`      | Inno Setup script of the Windows installer             |
| `macos/dmg_settings.py`         | Layout of the disk image window (dmgbuild)             |
| `macos/dmg_background.tiff`     | Disk image background, standard and Retina             |
| `macos/icon_1024.png`           | 1024 px app icon                                       |
| `linux/build_appimage.sh`       | Builds an AppImage in an AlmaLinux container           |
| `linux/com.sokteam.sok.desktop` | Desktop entry of the AppImage                          |
| `docker/entrypoint.sh`          | Entry point of the S.O.K Server image (`PUID`, `PGID`) |

The `Dockerfile` and `.dockerignore` of the S.O.K Server image are at the root.

## Workflows

| File                       | When it runs                                                                                                                                                                                                                                                                                                   |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ci.yml`                   | Pushes and pull requests to `develop` and `main`: lint, format, translations, type checks, tests on Linux and macOS, and the web interface (format, types, tests, build)                                                                                                                                       |
| `conventional-commits.yml` | Pull requests: checks the commit messages                                                                                                                                                                                                                                                                      |
| `release.yml`              | Pushes to `main`: semantic-release creates the version and a draft GitHub release; the three build workflows attach the packages to it and the image is pushed, the demo of S.O.K Server is put on the website, then the release is published, the website is rebuilt and `main` is merged back into `develop` |
| `build-linux.yml`          | Called by `release.yml`: builds the AppImages and attaches them to the release. By hand from the Actions tab: keeps them as an artifact of the run                                                                                                                                                             |
| `build-windows.yml`        | Same for the Windows installer                                                                                                                                                                                                                                                                                 |
| `build-macos.yml`          | Same for the macOS disk image                                                                                                                                                                                                                                                                                  |
| `build-docker.yml`         | Called by `release.yml`: builds the S.O.K Server image (amd64, arm64) and pushes it to GHCR. By hand: builds it without pushing                                                                                                                                                                                |
| `docs.yml`                 | Pushes to `main`, or by hand: publishes this documentation to GitHub Pages                                                                                                                                                                                                                                     |
