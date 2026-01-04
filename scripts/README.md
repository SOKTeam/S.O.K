# Utility Scripts

This folder contains utility scripts for development, build, and
maintenance of the S.O.K project.

## 📜 Available Scripts

### `build_sok.py`

The main script for compiling the application into a Windows executable (.exe) via
Nuitka.

```bash
python scripts/build_sok.py
```

**Functionality:**

- Securely injects keys from the `.env` file into the binary.
- Compiles Python code into optimized C++.
- Bundles all resources (images, translations) into the `dist/` folder.
- Generates the final installer (Inno Setup) if configured.

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
