---
title: Updates
description:
  How S.O.K finds a new release on GitHub and installs it on Windows, macOS and
  Linux.
---

S.O.K updates itself from the
[GitHub releases](https://github.com/SOKTeam/S.O.K/releases) of the project. The
code is in `sok/core/updater.py` (`UpdateManager`), with the interface in
`sok/ui/components/integrations/updates.py` and
`sok/ui/dialogs/update_dialog.py`.

## Checking

Two seconds after the window opens, if the "Check for updates" setting
(`check_updates`) is on, `check_and_show_updates()` starts an
`UpdateCheckWorker`. It calls `UpdateManager.check_for_updates()`:

1. A request to `https://api.github.com/repos/SOKTeam/S.O.K/releases/latest`,
   with a 5 second timeout. Drafts and pre-releases are not "latest", so they
   are never offered.
2. The tag of the release, without its `v`, is compared with `sok.__version__`
   (`packaging.version`). Only a newer version counts.
3. If there is one, the `UpdateDialog` opens in the GUI thread with the notes of
   the release (its description on GitHub).

A failed check (no network, GitHub unreachable) is only logged: the user sees
nothing.

## Installing

"Download and Install" asks `get_download_url()` for the file of this system,
found by the name of the release assets:

| System  | Asset                                                                                | What happens                                                                                                                |
| ------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| Windows | The `.exe` whose name contains `setup` (`SOK_Setup_v<version>.exe`), else any `.exe` | Downloaded into the temporary folder and started. S.O.K quits so that the installer can replace it                          |
| macOS   | The `.dmg` (`SOK_macOS_v<version>.dmg`)                                              | Downloaded into the temporary folder and opened in the Finder. S.O.K quits, and the user drags the new app over the old one |
| Linux   | The AppImage of this machine (`SOK_Linux_v<version>_<arch>.AppImage`)                | Downloaded next to the running AppImage, then put in its place. S.O.K restarts on the new file                              |

The download runs in a `DownloadWorker`, with a progress bar in the dialog.
Without a matching asset, the dialog opens the release page in the browser.

On Linux, the new AppImage is written as `<name>.part`, made executable and
renamed over the old file: the swap is atomic, and the file keeps its path, so
shortcuts and the applications menu entry still work. If the download fails, the
`.part` file is removed and the old AppImage stays. Outside an AppImage (run
from source, or a package of a distribution), S.O.K cannot replace itself and
opens the release page.

:::caution
The updater finds the assets by their names. Renaming a file in the release
workflows (`.github/workflows/build-*.yml`) breaks the updates of the versions
already installed. `tests/unit/test_updater_assets.py` checks the names it
expects.
:::

## Testing an update

The check compares with `sok.__version__`, so a build with an older version
finds the current release. To try it without publishing anything, build with a
lower version in `pyproject.toml`, then put the right one back before
committing: releases set the version with `scripts/bump_version.py`.

Keep in mind that:

- `UpdateDialog` must be created in the GUI thread. Before v1.3.0 it was created
  in the worker, and it crashed on Windows.
- The dialog takes its colors from the palette (`sok.ui.theme`). A color it
  asked for did not exist (`button_secondary`), and the dialog did not open
  (fixed in v1.3.1). Open the dialog in both themes after changing it.
