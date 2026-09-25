# Installation

## Installing on macOS

S.O.K runs on Macs with Apple Silicon (M1 or later).

1. Download `SOK_macOS_v<version>.dmg` from the S.O.K website.
2. Open it and drag **S.O.K** onto the **Applications** folder.
3. Open S.O.K from the Applications folder.

S.O.K is not notarized by Apple, so the first launch is blocked with a
message saying Apple cannot check it for malicious software. To allow it:

1. Click **Done** in that message.
2. Open **System Settings** > **Privacy & Security**.
3. Next to the message about S.O.K, click **Open Anyway**, then confirm.

You only need to do this once. Later updates downloaded by S.O.K itself
open the new disk image directly: drag the new app onto the old one.

Settings are stored in `~/Library/Application Support/S.O.K` and logs in
`~/Library/Logs/S.O.K`, so replacing the app keeps them.

## Requirements

- **Python 3.13+**
- **pip** or **uv** package manager

## Development Installation

### Clone the Repository

```bash
git clone https://github.com/SOKTeam/S.O.K.git
cd S.O.K
```

### Create Virtual Environment

=== "uv (recommended)"

```bash
uv venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

=== "venv"

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

### Install Dependencies

=== "uv (recommended)"

```bash
uv pip install -e ".[dev,docs]"
```

=== "pip"

```bash
pip install -e ".[dev,docs]"
```

## Dependencies Overview

### Core Dependencies

| Package | Purpose |
| --------- | --------- |
| `aiohttp` | Async HTTP client for API calls |
| `cryptography` | Secure credential storage |
| `mutagen` | Audio file metadata |
| `pypdf2` | PDF file handling |
| `pyside6` | GUI framework |
| `requests` | Sync HTTP client |
| `zstandard` | Compression support |

### Development Dependencies

| Package | Purpose |
| --------- | --------- |
| `pytest` | Testing framework |
| `pytest-asyncio` | Async test support |
| `ruff` | Linting and formatting |
| `mypy` | Static type checking |
| `ty` | Type checking |

### Documentation Dependencies

| Package | Purpose |
| --------- | --------- |
| `mkdocs` | Documentation generator |
| `mkdocs-material` | Material theme |
| `mkdocstrings-python` | Auto-generate docs from docstrings |

## Verify Installation

```bash
python -c "import sok; print(sok.__version__)"
```

## Building the macOS App

On a Mac with Apple Silicon:

```bash
python scripts/build_sok.py
```

The script compiles S.O.K with Nuitka into `dist/S.O.K.app` (ad-hoc
signed, as there is no Apple Developer ID) and packages it into
`dist/SOK_macOS_v<version>.dmg`.

## Building Documentation

```bash
mkdocs serve
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
