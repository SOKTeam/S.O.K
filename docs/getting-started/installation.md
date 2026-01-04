# Installation

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

## Building Documentation

```bash
mkdocs serve
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.
