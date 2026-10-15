---
title: Contributing
description:
  Branches, commit messages, checks and pull requests in the S.O.K repository.
---

Thank you for helping. Be respectful and constructive in issues and reviews, and
keep changes focused.

## Before you start

- Set up the project as described in
  [Set up a development environment](/getting-started/setup/).
- For a bug, check the
  [existing issues](https://github.com/SOKTeam/S.O.K/issues) first. For a larger
  change, open an issue to discuss it before writing the code.

## Branches

- `main` holds the released versions. Never commit to it directly.
- `develop` collects the work for the next release. Branches start from
  `develop` and pull requests target it.
- One branch per change, named after the commit type: `feat/drive-labels`,
  `fix/search-crash`, `docs/building-guide`.

## Commit messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org). The
release version is computed from them, so the type matters: `feat` gives a minor
version, `fix` and `perf` a patch, and a `!` after the type (or a
`BREAKING CHANGE:` footer) a major one.

```text
fix(apis): open a new HTTP session for each search worker

Each search worker runs its own event loop, and an aiohttp session can
only be used on the loop that created it.
```

- **Types**: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `style`,
  `build`, `ci`, `chore`, `revert`.
- **Scopes** (optional, but only from this list): `video`, `movies`, `music`,
  `books`, `games`, `images`, `ui`, `core`, `apis`, `config`, `file-ops`,
  `organize`, `i18n`, `deps`, `tools`, `macos`, `windows`, `linux`, `release`,
  `merge`.
- Write the subject in the imperative, in English, without a final period.
  Explain the why in the body.

The `lint` check of every pull request validates the messages with commitlint
(`.commitlintrc.json`).

## Checks

Run them before pushing; the CI runs the same ones on Linux, and the tests on
macOS too:

```sh
uv run ruff check src
uv run ruff format --check src
uv run python tools/verify_i18n.py
uv run mypy --install-types --non-interactive src/sok --ignore-missing-imports --no-strict-optional
uv run ty check src
uv run pytest tests/
```

## Code

- Type hints on new code, and Google-style docstrings on public functions and
  classes: they make the [API reference](/guides/documentation/#docstrings).
- `snake_case` for functions and variables, `PascalCase` for classes, a leading
  underscore for private members.
- Every text shown to the user goes through `tr()` and is added to the eight
  language files: see [Translations](/guides/translations/).
- Network calls are asynchronous and run in workers, never in the GUI thread.
- A change that affects one system (Windows, macOS, Linux) must leave the others
  unchanged.
- Add or update tests with the change.

## Pull requests

- Title in the Conventional Commits format, description in English: what
  changes, why, and how it was tested.
- Mention the effect on each system when the interface or the packaging changes.
- A pull request is merged when its checks pass and it has been reviewed.

## Reporting a bug

Open an [issue](https://github.com/SOKTeam/S.O.K/issues) with what you did, what
you expected and what happened, your system and the S.O.K version (_Settings →
About_). Attach the log: `sok.log`, whose location is given in
[Set up a development environment](/getting-started/setup/#run-the-app).
