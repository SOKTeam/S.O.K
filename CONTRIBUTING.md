# Contributing to S.O.K

Thank you for your interest in contributing to S.O.K (Storage Organization Kit)!
This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Git Workflow](#git-workflow)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Documentation](#documentation)
- [Internationalization (i18n)](#internationalization-i18n)
- [API Integration](#api-integration)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and
inclusive environment. Please:

- Be respectful and constructive in discussions
- Welcome newcomers and help them get started
- Focus on what is best for the community and the project
- Show empathy towards other community members

## Getting Started

### Prerequisites

- **Python 3.11+** (3.13 recommended)
- **Git** for version control
- **uv** (recommended) or pip for dependency management
- A code editor (VS Code recommended with Python extension)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/YOUR_USERNAME/Project-S.O.K.git
   cd Project-S.O.K
   ```

3. Add the upstream remote:

   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/Project-S.O.K.git
   ```

## Development Setup

### Using uv (Recommended)

```bash
# Install dependencies
uv sync

# Activate the virtual environment
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Run the application
uv run python src/sok/main.py
```

### Using pip

```bash
# Create virtual environment
python -m venv .venv

# Activate
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run the application
python src/sok/main.py
```

### IDE Configuration

For VS Code, recommended extensions:

- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Ruff (charliermarsh.ruff)

## Project Structure

``` bash
Project S.O.K/
├── src/sok/                 # Main source code
│   ├── apis/                # API integrations
│   │   ├── base_api.py      # Base API class
│   │   ├── video/           # Video APIs (TMDB, TVDB, IMDb, etc.)
│   │   ├── music/           # Music APIs (MusicBrainz, Deezer, etc.)
│   │   ├── books/           # Book APIs (Google Books, Open Library)
│   │   └── games/           # Game APIs (IGDB, RAWG)
│   ├── config/              # Configuration management
│   ├── core/                # Core utilities and interfaces
│   ├── file_operations/     # File handling operations
│   ├── media/               # Media type handlers
│   ├── resources/           # Static resources (icons, i18n)
│   └── ui/                  # PySide6 UI components
│       ├── components/      # Reusable UI components
│       ├── controllers/     # UI logic controllers
│       ├── pages/           # Main application pages
│       └── workers/         # Background workers
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   ├── functional/          # Functional tests
│   ├── acceptance/          # Acceptance tests
│   └── performance/         # Performance tests
├── docs/                    # Documentation source (MkDocs)
├── scripts/                 # Build and utility scripts
└── tools/                   # Development tools
```

## Coding Standards

### Python Style

We follow **PEP 8** with some project-specific conventions:

- **Line length**: 100 characters maximum
- **Imports**: Use absolute imports, grouped by standard library, third-party,
  and local
- **Docstrings**: Use Google-style docstrings in English
- **Type hints**: Required for all public functions and methods

```python
def process_media_file(
    file_path: Path,
    media_type: MediaType,
    options: Optional[Dict[str, Any]] = None
) -> ProcessResult:
    """
    Process a media file for organization.

    Args:
        file_path: Path to the media file to process.
        media_type: Type of media (video, music, book, game).
        options: Optional processing options.

    Returns:
        ProcessResult containing the operation status and details.

    Raises:
        FileNotFoundError: If the file does not exist.
        MediaTypeError: If the media type is not supported.
    """
    ...
```

### Code Quality Tools

We use **Ruff** for linting and formatting:

```bash
# Check for issues
ruff check src/

# Auto-fix issues
ruff check --fix src/

# Format code
ruff format src/
```

### Naming Conventions

| Type | Convention | Example |
| ------ | ------------ | --------- |
| Classes | PascalCase | `MediaManager`, `VideoApi` |
| Functions/Methods | snake_case | `get_media_info()`, `process_file()` |
| Constants | UPPER_SNAKE_CASE | `DEFAULT_TIMEOUT`, `API_BASE_URL` |
| Private members | Leading underscore | `_internal_cache`, `_process_item()` |
| UI Components | PascalCase with suffix | `SearchPanel`, `OptionsWidget` |

## Git Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test additions/updates

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```
feat(api): add support for TVDB API v4
fix(ui): resolve crash when no media files found
docs(readme): update installation instructions
refactor(file_ops): simplify batch rename logic
```

### Keeping Your Fork Updated

```bash
# Fetch upstream changes
git fetch upstream

# Merge into your branch
git checkout main
git merge upstream/main

# Push to your fork
git push origin main
```

## Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** following the coding standards
3. **Write/update tests** for your changes
4. **Update documentation** if needed
5. **Run the test suite** to ensure nothing is broken
6. **Push your branch** and create a Pull Request

### PR Checklist

- [ ] Code follows the project's coding standards
- [ ] All tests pass (`pytest tests/`)
- [ ] New code has appropriate test coverage
- [ ] Documentation is updated if needed
- [ ] Commit messages follow the convention
- [ ] PR description clearly explains the changes

### PR Review

- All PRs require at least one approval before merging
- Address all review comments
- Keep PRs focused and reasonably sized
- Use draft PRs for work-in-progress

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test category
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest tests/ --cov=sok --cov-report=html

# Run specific test file
pytest tests/unit/test_core_utils.py

# Run tests matching a pattern
pytest -k "test_media"
```

### Writing Tests

- Place tests in the appropriate directory based on type
- Use descriptive test names: `test_should_return_error_when_file_not_found`
- Use fixtures for common setup
- Mock external APIs and file system operations

```python
import pytest
from sok.file_operations import VideoOperations

class TestVideoOperations:
    """Tests for VideoOperations class."""

    @pytest.fixture
    def video_ops(self):
        """Create a VideoOperations instance for testing."""
        return VideoOperations()

    def test_should_extract_season_from_filename(self, video_ops):
        """Test season extraction from various filename formats."""
        assert video_ops.extract_season("Show.S01E05.mkv") == 1
        assert video_ops.extract_season("Show.Season.2.Episode.3.mkv") == 2

    def test_should_raise_error_for_invalid_file(self, video_ops):
        """Test that invalid files raise appropriate errors."""
        with pytest.raises(FileNotFoundError):
            video_ops.process("/nonexistent/file.mkv")
```

## Documentation

### Building Documentation

```bash
# Build docs
uv run mkdocs build

# Serve locally with hot reload
uv run mkdocs serve
```

### Documentation Guidelines

- Write documentation in English
- Use clear, concise language
- Include code examples where appropriate
- Keep documentation up-to-date with code changes
- Add screenshots for UI features

## Internationalization (i18n)

S.O.K supports multiple languages through the `tr()` function.

### Adding Translatable Strings

```python
from sok.ui.i18n import tr

# Always provide an English fallback
label = tr("settings.api_key", "API Key")
message = tr("error.file_not_found", "File not found")
```

### Translation Files

Translation files are located in `src/sok/resources/i18n/`:

- `en.json` - English (base)
- `fr.json` - French
- `pt.json` - Portuguese
- `es.json` - Spanish
- `de.json` - German
- `it.json` - Italian
- ...

### Adding Translations

1. Add the key and English text to `en.json`
2. Add translations to other language files
3. Use the `tr()` function in code with English fallback

### Verifying Translations

```bash
python tools/verify_i18n.py
```

## API Integration

### Adding a New API

1. Create a new file in the appropriate `apis/` subdirectory
2. Inherit from `BaseAPI`
3. Implement required methods
4. Register the API in `config/api_registry.py`

```python
from typing import List, Dict, Any, Optional
from sok.apis.base_api import BaseAPI
from sok.core.interfaces import MediaType, ContentType

class NewApi(BaseAPI):
    """
    Implementation for New API service.

    Documentation: https://api.example.com/docs
    """

    def __init__(self, api_key: str):
        """Initialize the API client."""
        super().__init__(api_key, "https://api.example.com/v1/")

    @property
    def supported_media_types(self) -> List[MediaType]:
        """Return supported media types."""
        return [MediaType.VIDEO]

    @property
    def supported_content_types(self) -> List[ContentType]:
        """Return supported content types."""
        return [ContentType.MOVIE, ContentType.TV_SERIES]

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for media content."""
        ...

    async def get_details(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a media item."""
        ...
```

### API Guidelines

- Use async/await for all network operations
- Implement proper error handling with `APIError`
- Respect rate limits
- Cache responses when appropriate
- Add comprehensive docstrings

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the bug
2. **Steps to reproduce**: Detailed steps to reproduce the issue
3. **Expected behavior**: What you expected to happen
4. **Actual behavior**: What actually happened
5. **Environment**: OS, Python version, S.O.K version
6. **Logs**: Relevant log output (from `logs/` directory)
7. **Screenshots**: If applicable for UI issues

### Feature Requests

For feature requests, please include:

1. **Description**: Clear description of the feature
2. **Use case**: Why this feature would be useful
3. **Proposed solution**: How you envision it working
4. **Alternatives**: Any alternative solutions considered

---

## Questions?

If you have questions about contributing, feel free to:

- Open a discussion on GitHub
- Check existing issues and discussions
- Review the documentation

Thank you for contributing to S.O.K!
