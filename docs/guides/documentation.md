---
title: Writing this documentation
description:
  Edit the guides, regenerate the API reference and preview the site with Kiln.
---

This site is built with [Kiln](https://github.com/Laidwin/kiln) from two
sources:

- **The guides**: the Markdown files of `docs/`, configured by `docs.yml` at the
  repository root (title, logo, accent color, sidebar).
- **The API reference**: rendered by Kiln under `/api/` from `api.json`, a
  description of the `sok` package that
  [griffe](https://mkdocstrings.github.io/griffe/) writes from the source code
  and its docstrings. `docs.yml` lists the modules left out (`api.exclude`): the
  interface, `sok.ui`, is not part of it.

`site/` and `api.json` are generated and ignored by git.

## Preview

Kiln runs in Docker, so the only requirement besides `uv` is Docker:

```sh
uv run --extra docs python scripts/build_docs.py serve
```

The site opens on <http://localhost:4321> and reloads when a page changes. After
changing docstrings, run `build_docs.py api` in another terminal: the reference
pages reload with the new `api.json`.

| Command                                  | Effect                                               |
| ---------------------------------------- | ---------------------------------------------------- |
| `build_docs.py` or `build_docs.py build` | Writes `api.json`, then builds the site into `site/` |
| `build_docs.py serve`                    | Writes `api.json`, then previews the site            |
| `build_docs.py api`                      | Only writes `api.json`                               |
| `build_docs.py clean`                    | Removes `site/` and `api.json`                       |

:::caution
Kiln reads every Markdown file in `docs/`, tracked by git or not. A
personal note left in that folder appears in your preview. Files and folders
whose name starts with `_` are ignored.
:::

## Write a page

Each page is a Markdown file with a front matter:

```md title="docs/guides/example.md"
---
title: Page title
description: One sentence, shown under the title and in search results.
---

Content in Markdown.
```

Add the page to the `sidebar` list of `docs.yml`, without the extension:
`guides/example`. Links between pages are absolute and end with a slash:
`[Building](/guides/building/)`.

Callouts use this syntax: `:::note`, `:::tip`, `:::caution` and `:::danger`,
closed by `:::`. Kiln's own documentation lists the other components.

Write for someone who knows Python but not S.O.K. Check every command and code
example against the code before publishing it.

## Docstrings

The API reference reads Google-style docstrings:

```python
async def search(self, query: str, content_type: ContentType, **kwargs: Any) -> Dict[str, Any]:
    """Search the service.

    Args:
        query: Text typed by the user.
        content_type: What to search for.
        **kwargs: Service-specific options, such as "language" or "year".

    Returns:
        A dictionary whose "results" key holds the matches.

    Raises:
        APIConnectionError: If the service cannot be reached.
    """
```

It covers `sok.core`, `sok.apis`, `sok.media`, `sok.file_operations` and
`sok.config`. The interface (`sok.ui`) is left out.
