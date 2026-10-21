---
title: Adding a page or a worker
description:
  Add a page to the window, run slow work in a background worker, and keep the
  interface translated, themed and responsive.
---

The interface, `sok.ui`, is left out of the
[API reference](/guides/documentation/): this guide describes its rules. For a
page that renames files in batches, start from `BatchPage` instead (see
[The path of a rename](/architecture/organizing/#adding-a-batch-page)).

## The golden rule

Qt widgets, and `QPixmap`, may only be created and changed in the GUI thread.
Everything slow (an API call, a folder scan, moving files) runs in a worker, in
another thread. A worker sends plain data through its signals (dictionaries,
lists, paths, bytes), and the page builds the widgets when the data arrives.

A widget created in a worker may work on one system and crash on another: the
update dialog did, on Windows only.

## Write a worker

Subclass `BaseWorker` (`sok/ui/workers/base.py`) and implement `execute()`:

```python title="src/sok/ui/workers/example_worker.py"
from PySide6.QtCore import Signal

from sok.core.media_manager import get_media_manager
from sok.ui.workers.base import BaseWorker


class ExampleWorker(BaseWorker):
    """Search a title in the background.

    Signals:
        progress (int, str): Percent complete and status message.
        finished (dict): The search results.
    """

    progress = Signal(int, str)
    finished = Signal(dict)

    def __init__(self, query, content_type, config=None):
        super().__init__(config)
        self._query = query
        self._content_type = content_type

    def execute(self):
        manager = get_media_manager()
        result = self._loop.run_until_complete(
            manager.search(self._query, self._content_type)
        )
        self.finished.emit(result)
```

`BaseWorker.run()` gives the worker its own asyncio event loop (`self._loop`)
and closes it at the end. It also catches the errors and emits `error` with a
message: for an `APIError` (missing key, quota used, no connection), the
translated sentence of `sok.ui.errors.error_message`. A worker that raises
always ends with `error`, never with silence.

Export the worker in `sok/ui/workers/__init__.py`.

## Run it from a page

`WorkerRunner` (`sok/ui/controllers/worker_runner.py`) moves the worker to a
`QThread`, connects its signals and runs the callbacks in the GUI thread:

```python
self._search_runner = WorkerRunner(self)

def _start_search(self, query):
    worker = ExampleWorker(query, ContentType.MOVIE)
    self._search_runner.run(
        worker,
        self._on_search_done,  # finished
        self._on_search_error,  # error: tell the user
        self._on_search_progress,  # progress, optional
        cancel_previous=True,
    )
```

A runner runs one worker at a time: starting another one first stops the current
one. By default it waits for it to end; `cancel_previous=True` aborts it
instead, for a search replaced by a newer one. Use one runner per kind of task
(search, rename…), so that a search does not stop a rename.

Without an `on_error` callback, the runner shows a generic error dialog. Prefer
your own: it can say what failed and put the page back in a usable state (enable
the buttons again, hide the progress bar).

## Add a page

A page is a widget, usually a `QScrollArea` with the object name `Page`. The
window places the pages in a `QStackedWidget` and selects them by **index**:

1. Create the page in `sok/ui/pages/` and export it in `pages/__init__.py`.
2. Add it in `MainWindow` (`main_window.py`) with `self._pages.addWidget()`, in
   sidebar order.
3. Add its sidebar button (the list of `(text_key, icon_name, index)` in
   `MainWindow`) and its title in `_nav_titles()`.
4. On macOS, add it to `PAGE_ACTIONS` in `macos_menu.py` (it gives the
   <kbd>Cmd</kbd>+<kbd>1</kbd>… shortcuts) and update `SETTINGS_PAGE`.
5. If the home page can send files to it, add its type to `PAGE_BY_KIND`.

:::caution
The indexes are written in several places. A page inserted in the middle shifts
the pages after it: check every index listed above, and the `navigate.emit()`
calls of the shortcuts of the home page (`home_page.py`).
:::

The window calls two methods of a page when it has them:

| Method            | Called                             | Does                                            |
| ----------------- | ---------------------------------- | ----------------------------------------------- |
| `retranslateUi()` | When the user changes the language | Sets every text of the page again with `tr()`   |
| `stop_workers()`  | When the window closes             | Stops the runners of the page (`runner.stop()`) |

Without `stop_workers()`, closing the window during a search can leave a thread
running.

## Texts

Every text goes through `tr(key, default)`, also in `retranslateUi()`. Add the
key to the eight language files: see [Translations](/guides/translations/).

## Look

The colors come from the main window stylesheet (`MainWindow`), which styles the
widgets by object name: `Page`, `PageTitle`, `Card`, `SectionLabel`, `Progress`…
Give a widget the object name of its role and it follows the theme, light or
dark. A widget without one keeps the Qt default: a progress bar without the name
`Progress` is blue instead of orange.

Other helpers of `sok.ui.theme` and `sok.ui.controllers`:

- `set_tone(widget, "ok")` colors a text with a tone of the palette (`ok`,
  `error`, `ambiguous`…).
- `card_shadow()` gives a card its shadow.
- `make_section_label(key, default)` makes a section title.
- `set_progress(bar, label, visible, message, value)` shows or hides a progress
  bar and its text.

Check a new page in both themes and on the three systems if you can: macOS uses
the native title bar and shows dialogs as sheets (`sok.ui.message_box`).
