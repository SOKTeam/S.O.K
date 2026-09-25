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

- Securely injects keys from the `.env` file into the binary.
- Compiles Python code into optimized C++.
- Bundles all resources (images, translations) into the `dist/` folder.
- Generates the final installer (Inno Setup) if configured.
- On macOS: builds `dist/S.O.K.app` (arm64, ad-hoc signed) and
  `dist/SOK_macOS_v<version>.dmg` with an Applications shortcut.

---

### `bump_version.py`

Keeps the application version identical everywhere. `pyproject.toml` is the
source of truth; the version is copied to `src/sok/__version__.py` and
`uv.lock`. The Windows executable gets it at build time (`build_sok.py`) and
the installer (`installation.iss`) reads it from the executable.

```bash
python scripts/bump_version.py 1.2.0   # write 1.2.0 everywhere
python scripts/bump_version.py --check # fail if a file is out of sync
```

Releases run it automatically (semantic-release) and the CI runs `--check`:
never edit these versions by hand.

---

### `build_docs.py`

Manages documentation generation and preview (MkDocs).

```bash
python scripts/build_docs.py [build|serve|clean]
```

**Options:**

- `build`: Generates the static site in `site/`.
- `serve`: Launches a local server at `http://127.0.0.1:8000`.
- `clean`: Removes previously generated files.

---

### `build_ui.py`

Automatically converts `.ui` files (Qt Designer) into PySide6-compatible Python
files.

```bash
python scripts/build_ui.py
```

**Typical usage:** Run after modifying an interface with Qt Designer.

---
