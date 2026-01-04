# Development Tools

This folder contains advanced tools designed to maintain code quality
and automate complex development tasks.

## 🛠️ Available Tools

### `verify_i18n.py`

Verifies consistency between translation keys used in the source code
and JSON language files.

```bash
python tools/verify_i18n.py
```

**Functionality:**

- Recursively scans the `src/` folder looking for `tr("key", ...)` calls.
- Compares these keys with those present in `src/sok/resources/i18n/*.json`.
- Reports missing translations or obsolete keys.

---

## 🔧 Scripts vs Tools

- **`scripts/`**: Daily and operational tasks (Build, UI, Simple tests).
- **`tools/`**: Code analysis, quality maintenance, and advanced utilities.

## 🎯 Suggested Next Steps

- `scaffold_page.py`: Structure generator for new UI pages.
- `api_mock_server.py`: Local server simulating TMDB responses for
offline development.
