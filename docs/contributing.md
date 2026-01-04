# Contributing

Thank you for your interest in contributing to S.O.K!

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive
environment:

- Be respectful and constructive in discussions
- Welcome newcomers and help them get started
- Focus on what is best for the community and the project
- Show empathy towards other community members

## Getting Started

### Prerequisites

- **Python 3.11+** (3.13 recommended)
- **Git** for version control
- **uv** (recommended) or pip for dependency management
- A code editor (VS Code recommended)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:

    ```bash
    git clone https://github.com/YOUR_USERNAME/S.O.K.git
    cd S.O.K
    ```

3. Add the upstream remote:

    ```bash
    git remote add upstream https://github.com/SOKTeam/S.O.K.git
    ```

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/S.O.K.git
cd S.O.K

# Create virtual environment
uv venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Install with dev dependencies
uv pip install -e ".[dev,docs]"
```

## Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check linting
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

## Type Checking

We use [mypy](https://mypy.readthedocs.io/) for static type checking:

```bash
mypy src/
```

## Testing

We use [pytest](https://pytest.org/) for testing:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sok --cov-report=html

# Run specific test file
pytest tests/unit/test_media_manager.py

# Run tests matching pattern
pytest -k "test_search"
```

### Writing Tests

- Place tests in the appropriate directory (`unit/`, `integration/`, `functional/`)
- Use descriptive test names: `test_should_return_error_when_file_not_found`
- Use fixtures for common setup
- Mock external APIs and file system operations

```python
import pytest
from sok.file_operations import VideoOperations

class TestVideoOperations:
    @pytest.fixture
    def video_ops(self):
        return VideoOperations()

    def test_should_extract_season_from_filename(self, video_ops):
        assert video_ops.extract_season("Show.S01E05.mkv") == 1

    def test_should_raise_error_for_invalid_file(self, video_ops):
        with pytest.raises(FileNotFoundError):
            video_ops.process("/nonexistent/file.mkv")
```

## Documentation

Documentation is built with MkDocs and auto-generated from docstrings:

```bash
# Serve locally
mkdocs serve

# Build static site
mkdocs build
```

### Writing Docstrings

We use Google-style docstrings:

```python
def search(self, query: str, content_type: ContentType) -> Dict[str, Any]:
    """Search for media items.

    Args:
        query: The search query string.
        content_type: The type of content to search for.

    Returns:
        A dictionary containing search results with 'results' key.

    Raises:
        APIConnectionError: If the API is unreachable.
        APIResponseError: If the API returns an error.

    Example:
        >>> api = TMDBApi(api_key="...")
        >>> results = await api.search("Inception", ContentType.MOVIE)
        >>> print(results["results"][0]["title"])
        'Inception'
    """
    ...
```

## Pull Request Guidelines

1. **One feature per PR**: Keep PRs focused on a single feature or fix
2. **Write tests**: Include tests for new functionality
3. **Update documentation**: Add docstrings and update docs if needed
4. **Follow code style**: Run linting before submitting
5. **Write clear commit messages**: Use conventional commits

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test additions/updates

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

## Project Structure

See [Project Structure](architecture/structure.md) for detailed information about
the codebase organization.

## Internationalization (i18n)

S.O.K supports multiple languages through the `tr()` function:

```python
from sok.ui.i18n import tr

# Always provide an English fallback
label = tr("settings.api_key", "API Key")
```

Translation files are in `src/sok/resources/i18n/`. To verify translations:

```bash
python tools/verify_i18n.py
```

## Adding a New API

1. Create a new file in the appropriate `apis/` subdirectory
2. Inherit from `BaseAPI`
3. Implement required methods (`search`, `get_details`)
4. Register the API in `config/api_registry.py`

```python
from sok.apis.base_api import BaseAPI

class NewApi(BaseAPI):
    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.example.com/v1/")

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        ...
```

## Reporting Issues

### Bug Reports

Include: description, steps to reproduce, expected vs actual behavior, environment
info, and logs.

### Feature Requests

Include: description, use case, proposed solution, and alternatives considered.

## Need Help?

- Open an issue for bugs or feature requests
- Join discussions for questions
- Check existing issues before creating new ones
