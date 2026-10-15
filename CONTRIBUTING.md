# Contributing to S.O.K

Thank you for helping! The full guide is in the developer documentation:
[docs/contributing.md](docs/contributing.md). It is also published with the
rest of the developer documentation (see [docs/](docs/)).

The essentials:

- **Setup:** Python 3.13 and [uv](https://docs.astral.sh/uv/), then
  `uv sync --extra dev` and `uv run sok`. See
  [docs/getting-started/setup.md](docs/getting-started/setup.md).
- **Branches:** start from `develop`, one branch per change
  (`feat/…`, `fix/…`, `docs/…`), and open the pull request against `develop`.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org).
  Scopes are optional but must come from the list in `.commitlintrc.json`
  (`ui`, `core`, `apis`, `file-ops`, `i18n`, `macos`, `windows`, `linux`…);
  the `lint` check rejects the others.
- **Checks:** the CI runs ruff (lint and format), `tools/verify_i18n.py`,
  mypy, ty and pytest. The commands are in the
  [contributing guide](docs/contributing.md#checks).
- **Texts:** every text shown to the user goes through `tr()` and is added to
  the eight files of `src/sok/resources/i18n/`.

Bugs and ideas go to the [issues](https://github.com/SOKTeam/S.O.K/issues).
