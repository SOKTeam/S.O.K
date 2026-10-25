# Utility Scripts

This folder contains utility scripts for development, build, and
maintenance of the S.O.K project.

## 📜 Available Scripts

### `build_sok.py`

The main script for compiling the application via Nuitka: a Windows executable
(.exe) on Windows, an Apple Silicon app bundle and disk image (.dmg) on macOS.

```bash
python scripts/build_sok.py
```

**Functionality:**

- Securely injects keys from the `.env` file into the binary. The build stops
  if `.env` is missing; pass `--allow-missing-keys` for a test build without
  API keys.
- Compiles Python code into optimized C++.
- Bundles all resources (images, translations) into the `dist/` folder.
- Generates the final installer (Inno Setup) if configured.
- On macOS: builds `dist/S.O.K.app` (arm64, ad-hoc signed) and
  `dist/SOK_macOS_v<version>.dmg` with dmgbuild: custom background,
  icon layout and Applications shortcut (`packaging/macos/dmg_settings.py`).
  Install the build extras first: `uv sync --extra build`.

---

### `make_macos_assets.py`

Draws the macOS artwork from vectors: the app icon (`logo.icns`, on the
macOS icon grid with the brand orange) and the disk image background
(`packaging/macos/dmg_background.tiff`, standard and Retina). Run it on
macOS after changing the logo or the colors.

```bash
python scripts/make_macos_assets.py
```

---

### `bump_version.py`

Keeps the application version identical everywhere. `pyproject.toml` is the
source of truth; the version is copied to `src/sok/__version__.py` and
`uv.lock`. The Windows executable gets it at build time (`build_sok.py`) and
the installer (`packaging/windows/installation.iss`) reads it from the
executable.

```bash
python scripts/bump_version.py 1.2.0   # write 1.2.0 everywhere
python scripts/bump_version.py --check # fail if a file is out of sync
```

Releases run it automatically (semantic-release) and the CI runs `--check`:
never edit these versions by hand.

---

### `build_docs.py`

Builds the developer documentation with Kiln (in Docker): the guides in
`docs/` and the API reference, which Kiln renders from `api.json`, a
description of the package written by griffe.

```bash
uv run --extra docs python scripts/build_docs.py [build|serve|api|clean]
```

**Options:**

- `build`: Writes `api.json`, then the static site in `site/`.
- `serve`: Writes `api.json`, then previews the site at `http://localhost:4321`.
- `api`: Only writes `api.json`.
- `clean`: Removes `site/` and `api.json`.

---

### `record_demo.py`

Records the data of the demo of S.O.K Server on the website
(`web/src/demo/data.json`). It creates a downloads folder of empty files in a
temporary folder, starts `sok-server` on it with the API keys of `.env`, lets
the automatic sorting rename a first part, renames a second part by hand,
analyzes the rest, then picks every candidate of every row to record its new
names. It takes about three minutes and needs the TMDB, Last.fm or Deezer, and
IGDB keys.

```bash
uv run --extra server python scripts/record_demo.py
cd web && npm run build:demo   # the demo, in web/dist-demo
```

Run it **by hand** when the API or the web interface changes what the demo
reads, and commit `data.json` with that change: the release builds the demo
and puts it on the website (`demo` job of `release.yml`), but never records
its data.

---

### `build_ui.py`

Automatically converts `.ui` files (Qt Designer) into PySide6-compatible Python
files.

```bash
python scripts/build_ui.py
```

**Typical usage:** Run after modifying an interface with Qt Designer.

---
