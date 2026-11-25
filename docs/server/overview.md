---
title: S.O.K Server
description: Running S.O.K Server from source, its JSON API, its database and its login.
---

S.O.K Server is the web version of S.O.K, for a NAS or a home server: a FastAPI
application in `sok/server/`, on the same core as the desktop app and without
Qt. The [user guide](https://sokfromsokteam.vercel.app/guide/server) explains
how to use it; this part describes how it is built.

## Running it from source

```sh
uv sync --extra dev
SOK_CONFIG_DIR=/tmp/sok-config uv run sok-server
```

`sok-server` (`sok.server.app:main`) listens on `http://0.0.0.0:8080`. Set
`SOK_CONFIG_DIR` to a test folder: the server keeps `sok.db`, its settings and
`logs/sok.log` there, never in those of the desktop app.

| Variable                       | Effect                                                                 |
| ------------------------------ | ---------------------------------------------------------------------- |
| `SOK_HOST`, `SOK_PORT`         | Address and port, `0.0.0.0` and `8080` by default                      |
| `SOK_CONFIG_DIR`               | Folder of the database, the settings and the log (`/config` in Docker) |
| `SOK_USERNAME`, `SOK_PASSWORD` | Create the account at startup, when none exists                        |
| `SOK_RESET_PASSWORD=1`         | With `SOK_PASSWORD`: replaces the password of the account at startup   |
| `SOK_AFTER_RENAME`             | A command run after each rename (see [Notifications](#notifications))  |
| `SOK_AUTH=none`                | Turns the login off, behind a reverse proxy that asks for one          |
| `SOK_LOG_LEVEL`                | Level of the log: `DEBUG`, `INFO` (default)…                           |
| `SOK_WEB_DIR`                  | Folder of the built interface, `web/dist` of the repository by default |

Without a built interface (no `index.html` in `SOK_WEB_DIR`), the server
answers only the API.

Only the `server` extra is needed to run it (`uv sync --extra server`): FastAPI,
uvicorn and argon2-cffi. The desktop build leaves `sok.server` out
(`--nofollow-import-to=sok.server`).

## Docker image

`ghcr.io/sokteam/sok-server`, built from the `Dockerfile` at the root:

```sh
docker build -t sok-server .
docker run -p 8080:8080 -v ./config:/config -v /mnt/storage:/data sok-server
```

- **Contents.** `python:3.13-slim-trixie`, the dependencies of the `server`
  extra installed by uv from `uv.lock` (no Qt), and `src/` without `sok/ui/`
  and `main.py`, run from there (`PYTHONPATH=/app/src`,
  `python -m sok.server.app`). `.dockerignore` lets in only `pyproject.toml`,
  `uv.lock`, `README.md`, `src/` and `packaging/docker/`: never `.env`, so the
  image has no key of the project.
- **Variables set by the image.** `SOK_CONFIG_DIR=/config`,
  `SOK_ENV_KEYS_WIN=1` (the keys given to the container win),
  `SOK_HOST=0.0.0.0`, `SOK_PORT=8080`, `PUID=1000`, `PGID=1000`. `TZ` works
  (tzdata is installed).
- **User.** `packaging/docker/entrypoint.sh` starts as root, gives `/config` to
  `PUID:PGID` and runs the server as that user (`setpriv`), so its files belong
  to the user of the NAS. The media folders keep their owners. Started with
  `--user`, the image runs as it is.
- **Health check.** `HEALTHCHECK` calls `GET /api/health` every 30 seconds.
- **Building it for a release.** `build-docker.yml`, called by `release.yml`,
  builds `linux/amd64` and `linux/arm64` (QEMU) with Buildx and pushes the tags
  `X.Y.Z`, `X.Y` and `latest` with the `GITHUB_TOKEN`. Run by hand, it builds
  both without pushing.

:::caution
The first push creates the package `sok-server` on GitHub as **private**. Make
it public once, in the package settings of the organization, so that users can
pull it without logging in.
:::

## Code

| File                                          | Contents                                                                             |
| --------------------------------------------- | ------------------------------------------------------------------------------------ |
| `server/app.py`                               | `create_app(folder)`, the logging and `main()`                                       |
| `server/db.py`                                | `Database`: `sok.db` and its migrations                                              |
| `server/auth.py`                              | `Accounts`: the account, the password check, the sessions; `auth_disabled()`         |
| `server/api/auth.py`                          | The routes of the account and the session, and `require_login`                       |
| `server/api/health.py`                        | `GET /api/health`                                                                    |
| `server/settings.py`                          | `Settings`: the settings, the keys, the folders, the notifications; `check_link()`   |
| `server/api/settings.py`                      | The routes of the settings                                                           |
| `server/scans.py`                             | `Scans`: the analyses, the rows, the files to check                                  |
| `server/events.py`                            | `EventBus`: the events sent to the browsers                                          |
| `server/api/scans.py`, `server/api/events.py` | The routes of the analyses and `GET /api/events`                                     |
| `server/search.py`, `server/api/rows.py`      | `Searcher`: the search of the rows, their changes and what the tabs show; its routes |
| `server/jobs.py`                              | `Jobs`: the slot of the background work, one analysis or one rename at a time        |
| `server/renames.py`                           | `Renamer`: the renames                                                               |
| `server/history.py`                           | `History`: the rename history in the database                                        |
| `server/api/renames.py`                       | The routes of the renames and of the history                                         |
| `server/api/web.py`                           | Serves the built interface (`web/dist`)                                              |
| `server/watcher.py`, `server/api/watch.py`    | `Watcher`: the automatic sorting of the source folders; `GET /api/watch`             |
| `server/notify.py`                            | `Notifier`: Discord, Jellyfin, Plex, a webhook and a script after each rename        |

`create_app()` opens the database when the application starts (its lifespan),
creates the account from `SOK_USERNAME` and `SOK_PASSWORD` if needed, and puts
the `Database`, the `Accounts`, the `ConfigManager` and the `Settings` in
`app.state`. The routes read them from the request. A new database is a new
installation: `create_app()` then sets the file mode to `link`, the default of
the server (the desktop app moves).

## API

JSON under `/api`. FastAPI's own `/docs` page is turned off.

| Route                                  | Login | Does                                                                                                 |
| -------------------------------------- | ----- | ---------------------------------------------------------------------------------------------------- |
| `GET /api/health`                      | No    | `{"status": "ok", "version", "db"}`, for the health check of Docker                                  |
| `GET /api/session`                     | No    | `auth` (`login` or `none`), `account`, `logged_in`, `username`                                       |
| `POST /api/setup`                      | No    | Creates the account (`username`, `password`) and logs in; once only (`409`)                          |
| `POST /api/login`                      | No    | Opens a session (`401` for a wrong login, `429` while waiting)                                       |
| `POST /api/logout`                     | Yes   | Closes the session                                                                                   |
| `GET /api/i18n?lang=fr`                | No    | The texts of the interface (see [Interface](#interface))                                             |
| `GET /api/settings`                    | Yes   | The settings, the keys, the folders and the link checks (see below)                                  |
| `PATCH /api/settings`                  | Yes   | Changes some of them (`settings`, `keys`, `folders`); answers like `GET`                             |
| `POST /api/settings/test-link`         | Yes   | `{source, destination}`: whether a hard link works between them                                      |
| `GET /api/settings/disks`              | Yes   | The disks of the folders and the average size of the movies waiting (see [Analyses](#analyses))      |
| `GET /api/settings/browse?path=`       | Yes   | The subfolders of a folder of the server, for the folder browser (`404` `unreadable_folder`)         |
| `POST /api/settings/test-key`          | Yes   | `{service, key?, secret?}`: whether a key works (see [Testing a key](#testing-a-key))                |
| `POST /api/settings/test-notification` | Yes   | `{target}`: sends a test (see [Notifications](#notifications)); answers `{"ok", "error"}`            |
| `POST /api/scans`                      | Yes   | Starts an analysis (`202`, `{"id"}`); `409` with `already_running`, `rename_running` or `no_sources` |
| `GET /api/scans/current`               | Yes   | The last analysis, the counts of the rows and the files to check (see [Analyses](#analyses))         |
| `POST /api/to-check`                   | Yes   | `{path, kind}`: gives a file to check its type and searches its row; answers the summary             |
| `GET /api/events`                      | Yes   | Server-sent events (see [Live events](#live-events))                                                 |
| `GET /api/watch`                       | Yes   | The automatic sorting: on or off, last check, last run (see [Automatic sorting](#automatic-sorting)) |
| `GET /api/rows?type=movies`            | Yes   | The rows of a tab (see [Rows](#rows))                                                                |
| `GET /api/rows/{id}`                   | Yes   | One row                                                                                              |
| `PATCH /api/rows/{id}`                 | Yes   | `{selected?, destination?}`: picks a candidate (the row is then Ready) or a destination folder       |
| `POST /api/rows/{id}/search`           | Yes   | `{query?}`: searches the row again, with the text typed; `409` when a key stops it                   |
| `POST /api/renames`                    | Yes   | `{type, rows?}`: renames the Ready rows of a tab (`202`, `{"id"}`); see [Renames](#renames)          |
| `GET /api/renames/current`             | Yes   | The last rename: its progress, then its result                                                       |
| `GET /api/history`                     | Yes   | The operations of the history, newest first (see [History](#history))                                |
| `POST /api/history/{id}/undo`          | Yes   | `{index?}`: undoes the operation, or one of its files; answers what was put back                     |
| `GET /api/processed`                   | Yes   | The files already processed (see [Files already processed](#files-already-processed))                |
| `POST /api/processed/forget`           | Yes   | `{paths}`: the next analysis takes these files again; answers `{"forgotten"}`                        |

The interface starts with `GET /api/session`: no account → the setup page; an
account and no session → the login page; otherwise the app.

A route that needs a session declares `dependencies=[Depends(require_login)]`;
without one, it answers `401` with `"not_logged_in"`. The errors give a code in
`detail` (`account_exists`, `invalid_account`, `wrong_login`,
`too_many_attempts`, `not_logged_in`) that the interface translates.

## Interface

The interface is built by Vite into `web/dist`; `api/web.py` serves it after
the API routes. A path that is a file of the build answers that file
(`assets/` with a hash in its name, kept a year by the browser); any other path
not under `/api` answers `index.html` (asked again each time), and the
interface shows the page of its address. An unknown `/api` path keeps its JSON
`404`.

There is one language, the `language` setting: it names the season folders and
translates the interface. At the first visit, the setup sends the language of
the browser (`POST /api/setup` with `language`), kept when S.O.K has it.
`GET /api/i18n` answers `language`, `languages` and `texts`, the translation
file of `src/sok/resources/i18n/` (the same as the desktop app): of `lang` when
S.O.K has it, else of the settings. It needs no login, for the setup and login
pages.

### The web project

`web/` is a Svelte 5 application in TypeScript, built by Vite, styled with
Tailwind CSS 4. Node is only needed to build it: the Docker image builds it in a
`node` stage and keeps only `web/dist`; `web/dist` is never committed.

```sh
cd web
npm ci
npm run dev     # http://localhost:5173, /api sent to SOK_API (localhost:8080)
npm run format  # Prettier, with the Svelte plugin and the Tailwind class order
npm run check   # svelte-check (types)
npm test        # Vitest
npm run build   # web/dist, served by sok-server
npm run dev:demo    # the demo of the website, http://localhost:5173/demo/
npm run build:demo  # web/dist-demo; release.yml puts it on the website
```

During development, run `sok-server` next to `npm run dev`: Vite reloads the
interface at each change and sends the `/api` requests to the server.

| File                         | Contents                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/App.svelte`             | The first page: setup without an account, login without a session, else the app (directly with `SOK_AUTH=none`)                                                                                                                                                                                                                                                                                                                                |
| `src/pages/`                 | `Setup`, `Login`, `Shell` (the navigation, the light of the scene and the page of the address), `Analysis`, `MediaScreen` (the screen of a media type), `History` (with `/history/processed`), `Settings`                                                                                                                                                                                                                                      |
| `src/components/`            | `nav/NavBar` (the typographic navigation) and `nav/Cube` (the logo cube), `layout/Split` (a screen: the list, then the scene), `scene/Fan` (covers fanned out) and `scene/Facts` (a dotted sheet), `media/Thumb` (a poster, a cover, a book or a tile, with the mark of the selection) and `media/Gauge` (the 5 notches), `settings/*` (the lines of the Settings, the folder browser `FolderPicker`, the dial `SortDial`), `AuthCard`, `Icon` |
| `src/lib/api.ts`             | `api()`: calls `/api` with the session cookie; an error is an `ApiError` with the `code` of `detail`; `openEvents()`: `GET /api/events`; in the demo build, both go to `src/demo/server.ts`                                                                                                                                                                                                                                                    |
| `src/lib/errors.ts`          | The texts of the errors of the API, of a stopped analysis, of a hard link problem and of an automatic sorting                                                                                                                                                                                                                                                                                                                                  |
| `src/lib/format.ts`          | `fill()`, `pickLanguage()`, `parentFolder()`, `splitName()`, `dayKey()`, `daysAgo()`, `pluralForm()` (the plural rules of the desktop app)                                                                                                                                                                                                                                                                                                     |
| `src/lib/i18n.svelte.ts`     | `loadTexts()`, `t(key, english, values)`, and `tn(key, n, one, other, values)` for a text with a number (keys `<key>_one`, `_few`, `_many`, `_other`)                                                                                                                                                                                                                                                                                          |
| `src/lib/router.svelte.ts`   | The page is the path of the address (`/movies`), under the base of the build (`/demo/` for the demo); `navigate()`, `follow` and `href()` for the links                                                                                                                                                                                                                                                                                        |
| `src/lib/session.svelte.ts`  | `GET /api/session`, `logOut()`                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `src/lib/scan.svelte.ts`     | The summary of the analysis, kept live by `listen()` (`GET /api/events`); `startScan()`, `confirmType()`                                                                                                                                                                                                                                                                                                                                       |
| `src/lib/rows.ts`            | `loadRows()`, `changeRow()`, `searchRow()`, `posterUrl()`, `bigPosterUrl()`, `matchOf()`, `titleOf()`, and what the screens read from the names: `episodeCode()`, `episodeTitle()`, `seasonsOf()`, `trackOf()`, `formatOf()`, `platformOf()`                                                                                                                                                                                                   |
| `src/lib/renames.svelte.ts`  | The last rename, kept live by the `rename` and `progress` events; `startRename()`                                                                                                                                                                                                                                                                                                                                                              |
| `src/lib/history.ts`         | `loadHistory()`, `undo()`, `loadProcessed()`, `forgetProcessed()`                                                                                                                                                                                                                                                                                                                                                                              |
| `src/lib/settings.svelte.ts` | `loadSettings()`, `saveSettings(change)`, `testKey(service, key?, secret?)`                                                                                                                                                                                                                                                                                                                                                                    |
| `src/lib/theme.svelte.ts`    | The theme of the browser (`dark`, the default, `light` or `system`, in `localStorage`; the old `orange` becomes `light`), set as `data-theme` on `<html>`; `startTheme()`, `chooseTheme()`                                                                                                                                                                                                                                                     |
| `src/lib/watch.svelte.ts`    | The state of the automatic sorting (`GET /api/watch`), kept live by the `watch` events; `loadWatch()`                                                                                                                                                                                                                                                                                                                                          |
| `src/lib/namePreview.ts`     | `previewPath()`: the path an example file gets with a name model, for the preview of the Settings (tested)                                                                                                                                                                                                                                                                                                                                     |
| `src/lib/pages.ts`           | The pages of the navigation                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `src/lib/icons.ts`           | The icons of the desktop app (`src/sok/resources/assets`), in the color of the text                                                                                                                                                                                                                                                                                                                                                            |
| `src/lib/light.svelte.ts`    | The color of the light of the scene; `setLight()`                                                                                                                                                                                                                                                                                                                                                                                              |
| `src/lib/color.ts`           | `posterColor()`: the color of a poster, for the light (when its server allows reading it)                                                                                                                                                                                                                                                                                                                                                      |
| `src/lib/disks.ts`           | `loadDisks()`, `sizeText()`                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `src/lib/site.ts`            | `SITE_URL`, the website of the help links                                                                                                                                                                                                                                                                                                                                                                                                      |
| `src/app.css`                | Tailwind, the colors of the art direction (`bg-surface`, `text-muted`…), Geist and Geist Mono (`public/fonts`), and the shared classes (`key`, `key-primary`, `key-sm`, `legend`, `field`, `label`, `link`, `tag`)                                                                                                                                                                                                                             |

- **Colors.** `app.css` declares the colors of the SOKTeam art direction
  (`.impeccable/refs/direction-artistique/tokens.json`, the same as
  `src/sok/ui/tokens.py`) in `@theme`, the dark theme being the default;
  `:root[data-theme="light"]` only changes the variables. Use these colors
  (`bg-bg`, `bg-surface`, `bg-raised`, `bg-key`, `text-ink`, `text-muted`,
  `text-faint`, `border-line`, `bg-accent`, `text-on-accent`,
  `text-accent-text`, `text-caution`, `text-danger`…), never a color of
  Tailwind's palette. The coral is for the primary key, the counts of the open
  page and what asks for a choice; caution for what is missing.
- **Style.** The look of the desktop app: a typographic navigation at the top
  (`NavBar`), a title that is a sentence ending with a period, the list on the
  left and the lit scene on the right (`Split`), dotted sheets (`Facts`), keys
  lit from above. A screen has one primary key (`key key-primary`); the others
  are `key`, `key-sm` in rows. The light of the scene (`setLight()`) takes the
  color of the poster shown, painted by `Shell` behind the whole window. While
  the screens move to this look one by one, `app.css` keeps the old names
  (`bg-card`, `text-fg`, `button`…) as aliases of the new colors.
- **Texts.** Every text goes through `t("web_key", "English text")`, with the
  keys in the translation files of the desktop app (see
  [Translations](/guides/translations/)). The keys of the desktop app can be
  reused (`movies`, `settings`); the new ones start with `web_`.
- **Settings page.** One page that scrolls, as the Settings of the desktop
  app: a block per part, its title at the left and dotted lines at the right
  (`components/settings/`: `Line`, `Choice` for words to pick, `Switch`,
  `OpenBox` for what an open line sets). The blocks: **Folders** (the
  sources, then the destinations of each type, the first one "default";
  `FolderRole`), **Behavior** (the file mode, the hard link problems, the
  switches), **Automatic sorting**, **Notifications**, **File names**,
  **Sources** (per media type: "Searched first", then each service and the
  state of its key: free, set, to set up, set by an environment variable),
  **Appearance** (theme of the browser, language), **Account** and
  **About** (version, data folder, documentation). Each block has its
  address (`/settings/auto`, `/settings/sources`…; `/settings` is Folders):
  the page goes to the block of the address, and while it scrolls it
  replaces the address with the block read (`replace()` in
  `router.svelte.ts`). The addresses of the tabs of before 1.6 still work
  (`/settings/rename`, `/keys`, `/look`). Each change is saved at once
  (`PATCH /api/settings`; the answer replaces the settings shown): a switch,
  a word, a folder, a model or a key with its Save key. One line opens at a
  time: a key (its fields, Save, Test, Remove, "Get a key"; Test tries the
  key typed, else the saved one), a target of the notifications (its fields,
  Save, Test once set, Remove), a name model (its field and its fields
  `{title}`…). A refused change shows its error at the top (a folder: under
  its role). **Browse…** opens the folder browser in the scene
  (`FolderPicker`: the folders of the server, its path can be typed), next
  to the last folder of the role, or next to the sources. In `link` mode,
  each hard link that cannot be made shows under the file mode, in a caution
  box (the problem, why, what to change, **Use Copy**, **Got it**; a problem
  read comes back only if it is new); when the links work, the page says so.
  A new language loads its texts at once. The scene is a live preview that
  follows the block read: the example file of a type, before and after, the
  parts filled by S.O.K in coral (`previewPath()` in `lib/namePreview.ts`,
  as `fill_format` and `format_name`; the type of the model open, or of the
  folder browsed); the rhythm of the automatic sorting (`SortDial`: an hour,
  the looks marked, the minutes before the next one, the last automatic
  renames); the message Discord gets after the last rename (as `_message()`
  in `notify.py`) and the apps told; the account.
- **Analysis and tabs.** `Shell` listens to `GET /api/events` for every page:
  a `scan` event replaces the summary (the counts of the navigation, the
  analysis page) and makes the open tab read its rows again; `progress`
  events move the progress bar, and the counts are read again once the files
  are sorted. The analysis page says hello and when the last analysis ran,
  how many files wait ("20 files to sort."), where and how often the
  automatic sorting looks, then a row per media type with files (its covers,
  its count, recognized / to pick / not found, **See**), the files to check
  with a key per type they hesitate between, the last rename with its undo
  (confirmed in place), **Analyze** and the files already processed. While an
  analysis runs, its title and a bar say where it is. Its scene shows the
  covers waiting, the source folders with their files (a missing one in
  caution) and the disks with the room left.
  Every media type has its screen (`MediaScreen`) says how many movies
  wait, where they were found and how many are recognized, to pick or not
  found; the filters are words with their counts. A row: poster, title and
  year, "was <file name>", and the 5-notch gauge, or "to pick" / "not found".
  Clicking a row opens its scene: the poster (its color lights the scene),
  title, year, a dotted sheet (quality and size from the row, file mode, the
  preferred service of the settings), "Will be put here" with the new path
  and, when the media type has several, the destination folders as words.
  "That's not it" (or a row to pick or not found) opens the results to pick
  (poster, title, year and artist or authors, overview) and a search field.
  **Selection**: the round mark at the top-left of a poster (on hover), a
  Cmd/Ctrl-click or a Shift-click enter the selection mode, where every mark
  shows and a click toggles a row (Shift: a range); only Ready rows can be
  chosen. The scene then fans the covers chosen. "Done" or Escape leave it.
  On TV Shows, a row is a series: the screen counts its episodes ("23
  episodes to sort.", "In 4 series."), the row says its seasons and episodes,
  the open series unfolds its episodes under its row (code, title, "was …",
  the first 4 then "+ N other episodes"), and its scene shows "Series · year",
  the title, the seasons and the titles found, a grid of the episodes (faint
  without a title) and the folder of the season. `episodeCode()`,
  `episodeTitle()` and `seasonsOf()` (`lib/rows.ts`) read them from the new
  names, else the file names.
  On Music, the screen counts tracks ("In 24 albums.", "And 3 single
  tracks."), the rows are a grid of square covers (title, artist · year; the
  open album on the raised ground, the chosen ones ringed in coral), and the
  scene shows the cover, "artist · year · N tracks", the first 6 tracks
  (`trackOf()` reads their number and title) then "+ N tracks", and the
  folder of the album. "Which album is it?" or "Which track is it?" follows
  the kind of the row.
  On Books, the thumbnails have the corners of a spine and its shade; a row
  gives the authors and the format (EPUB, PDF) as a tag; the sheet of the
  scene gives the publisher, the format and size, the ISBN (`publisher` and
  `isbn` of the result, when its service gives them) and the service; a note
  says that the books not recognized stay where they are.
  A screen opens its first Ready row; without one, the first row on its
  results.
  On Games, a row gives the console as a tag (`platformOf()`: the first
  folder of the new name). A media type with nothing to sort shows the empty
  screen: three empty slots, "No game to sort.", what S.O.K does with these
  files, **Analyze** and **How it works** (the guide of the website,
  `SITE_URL` of `lib/site.ts`), and for Games the consoles recognized. The
  end of a rename stays on its scene even when it empties the list.
- **Renames and history.** The primary key of a media screen puts away its
  Ready rows ("Put away the movies N"), or the selection ("Put away the
  selection N"), at once (`POST /api/renames`); a note under the list says
  what the file mode does. While it runs, the title and the lead give the
  progress; at the end, the scene says how many files were put away, the
  subtitles, the files left in place and why, with "Undo this" (confirmed in
  place), "See the history" and "Close". The renamed rows leave the list at
  the `rename` event that ends it.
  The History page (`History`, sections from `sectionsOf()` in
  `lib/historyGroups.ts`) lists the renames newest first: "Today",
  "Yesterday · <date>", "Earlier in <month>" for the month of the newest
  one, then one folded line per older month ("14 renames in October, 611
  files", **Show**). A row: time (or day), the covers its rename kept,
  "6 movies put away", from where to where, the tag `auto` and "Undone" /
  "Partly undone". Its scene: the covers fanned out, when, the title, a
  dotted sheet (put away by you or the automatic sorting, from, to, the
  transfer), the first files with "was …" (a subtitle "follows its video")
  and ↺ to put one back, then **Undo this** (or **Undo the rest**). Every
  undo is confirmed in the scene, then the scene says what came back and
  what stayed, and why. **Already processed** (`/history/processed`, linked
  from the analysis page) lists the files the analyses leave out (cover of
  their operation, name, new name and mode, date, size), chosen with the
  selection of the media screens; **Analyze again N** forgets them and starts
  an analysis. Its scene counts them per source folder, hard links and
  copies. Without any rename, the page is the empty screen.
- **Automatic sorting.** The settings turn it on after a confirmation in
  place (the ready files will be sorted on their own, with the file mode
  named) and set
  the minutes between two checks. The strip of the analysis page shows
  whether it is on, its last run (files renamed) and its last check (on hover);
  each problem shows with the others (`watchProblemText` in `errors.ts`: the
  stop of the analysis, or the tab and why its rename was refused). An
  automatic analysis says so after its date.
- **Notifications.** One line per target, on or off; open, its fields (an
  address is shown again, a secret only as saved), Save, Remove, and a test
  once it is set (`POST /api/settings/test-notification`). The script line
  only says whether `SOK_AFTER_RENAME` is set.
- **Language at startup.** Without an account, the interface asks
  `GET /api/i18n` for the languages, then loads the first language of the
  browser that S.O.K has (`pickLanguage`); the setup sends it to the server.
  With an account, it loads the language of the settings.
- **Demo.** The website shows the interface at `/demo/` without a server:
  `npm run build:demo` (Vite's `demo` mode) builds it with the base `/demo/`
  into `web/dist-demo`, and `api()` and `openEvents()` answer from
  `src/demo/server.ts`, a server in TypeScript that keeps its state in the
  page (loading it again starts again) and changes no file. It answers from
  `src/demo/data.json`, the answers of a real `sok-server` recorded by
  `scripts/record_demo.py` (see [Scripts](https://github.com/SOKTeam/S.O.K/tree/main/scripts)):
  the rows, the new names of each candidate, two searches, the file to
  check, the history, the settings, and a file that arrives 40 seconds after
  the opening for the automatic sorting to rename. The other searches find
  nothing. The language is the one of `?lang=` (the links of the website give it), else the browser's; the banner of `Shell` says that
  nothing is renamed and credits TMDB. Below 768 pixels,
  `demo/MobileNotice.svelte` first fills the screen: S.O.K Server is not
  made for a phone, "Continue anyway" (once per tab) or back to the site. The
  `demoPreview` plugin of `vite.config.ts` gives its page the preview of a
  shared link (Open Graph and Twitter tags, with the image `/og-demo.png` of
  the website, whose address is the `SITE` constant). The normal build holds
  none of it: `import.meta.env.MODE` is fixed at build time
  and the demo is loaded with `import()`. At each release, the `demo` job of `release.yml`
  builds it and puts it on the website (see
  [Releases](/guides/building/#releases)). **The data are not recorded
  again by the release**: when a change of the API or of the interface
  changes what the demo reads (a field, a route, an event), run
  `scripts/record_demo.py` by hand and commit `data.json` with the change.
- **CI.** The `Web interface` job of `ci.yml` runs `npm ci`, `format:check`,
  `check`, `test` and `build` on every pull request.

## Login

- **The account**: one row of the `account` table. The user name is not empty,
  the password has at least 8 characters (`MIN_PASSWORD_LENGTH`). The password
  is hashed with Argon2 (`argon2-cffi`), and hashed again at the next login when
  the parameters of Argon2 change. A forgotten password: start the server
  with `SOK_RESET_PASSWORD=1` and the new password in `SOK_PASSWORD`
  (`Accounts.reset_from_env`): the password is replaced (and the user name, with
  `SOK_USERNAME`), the sessions are closed, and nothing else changes. Remove
  the variable afterwards; the log reminds it.
- **The session**: a random token in the `sok_session` cookie, `HttpOnly`,
  `SameSite=Strict`, for 30 days; `Secure` when the request comes over HTTPS.
  The database only keeps the SHA-256 of the token, so a copy of `sok.db` opens
  no session. Expired sessions are deleted at the next login.
- **Failed logins**: after 5 in a row, every attempt is refused for 30 seconds
  after the last failure (`429` with `Retry-After`). A success starts the count
  again. The count is in memory: a restart clears it.
- **`SOK_AUTH=none`**: every route answers without a session, and
  `GET /api/session` says `"auth": "none"` for the interface to show its warning.

## Settings

`GET /api/settings` answers:

| Field           | Contents                                                                                                                                                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `settings`      | `language`, `file_mode`, the behavior switches, the five name formats, the service of each media type (`preferred_api_video`, `_music`, `_books`, `_games`), `auto_sort` and `auto_sort_minutes` (`SETTINGS` in `settings.py`) |
| `languages`     | The languages of the interface                                                                                                                                                                                                 |
| `services`      | The services each `preferred_api_*` can pick, per media type (`video`, `music`, `books`, `games`): `{"id", "name"}`                                                                                                            |
| `keys`          | Each service (`service`, `name`, `media_type`, `url` to get a key) and its keys: `{"key", "set", "locked"}`, never the value                                                                                                   |
| `folders`       | `sources`, and the destination folders of `movies`, `tv`, `music`, `books`, `games`, in order                                                                                                                                  |
| `link_checks`   | In `link` mode, one check per source and destination: `ok`, `problem`, `tested`                                                                                                                                                |
| `notifications` | `discord`, `webhook`: `{"set"}`; `jellyfin`, `plex`: `{"url", "set"}`; `script`: whether `SOK_AFTER_RENAME` is set (see [Notifications](#notifications))                                                                       |
| `about`         | `version` of the server, and `data`: the folder of its database (`SOK_CONFIG_DIR`, `/config` in Docker)                                                                                                                        |

- **Where they are kept.** The settings and the keys shared with the desktop
  app stay in `config.json`, through the `ConfigManager`: the core reads them
  there. The folders, which only the server has, are in the `folders` table,
  and the settings of the server only (`SERVER_SETTINGS`: `auto_sort`, off by
  default, and `auto_sort_minutes`, 5 by default, from 1 to 1440) in the
  `options` table.
- **Changing them.** `PATCH /api/settings` takes any of `settings`, `keys`,
  `folders` and `notifications`. Everything is checked before anything is saved; the first problem
  answers `422` with `{"code", "item"}` in `detail`: `unknown_setting`,
  `invalid_value`, `unknown_key`, `key_locked`, `unknown_folder_role`,
  `invalid_folder` (not an absolute path to an existing folder, as the server
  sees it), `invalid_url` (a notification address without `http://` or
  `https://`).
- **Keys.** An empty value removes a key. A key is `set` when the settings or an
  environment variable give it, and `locked` when an environment variable wins
  over it (`SOK_ENV_KEYS_WIN`, see
  [Where an API key comes from](/reference/settings/#where-an-api-key-comes-from)):
  a locked key cannot be changed. Only the keys that `config.json` can hold are
  listed. After a change of keys or of a preferred service, the media manager
  is built again for the next search.
- **Folders.** Each role given replaces its list; paths are normalized and
  duplicates dropped.
- **Browsing.** The browser cannot see the disks of the server:
  `GET /api/settings/browse?path=` (`browse()` in `settings.py`) lists the
  subfolders of a folder, hidden ones left out, sorted by name, 1000 at most,
  with its `parent` (`null` at the root); without `path`, the root. A path
  that is not an absolute folder, or cannot be read, answers `404`
  `unreadable_folder`.

### Link checks

`check_link(source, destination)` gives a `problem` when a hard link cannot
work:

| `problem`          | When                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------- |
| `missing_folder`   | One of the folders is gone                                                            |
| `different_drives` | Not the same device: two drives, or two Docker mounts even on one disk                |
| `no_hard_links`    | A test link of a file of the source fails (FAT, exFAT, network shares, no permission) |

The test link is made with `can_hard_link` and deleted at once. A source with no
file yet is only compared by device (`"tested": false`).

### Testing a key

`POST /api/settings/test-key` takes a service id and, to test a key before
saving it, `key` (and `secret` for Spotify and IGDB). Without them it tests the
saved key. It answers `{"service", "status", "detail"}`, never the key; `detail`
is the message of the service.

`sok.apis.key_check.check_key()` (no Qt) makes one light request per service,
which needs the key and nothing else (`PROBES`): TMDB `/authentication`, the
TVDB login, the Spotify and Twitch (IGDB) token, a small search or lookup for
the others. The API clients cannot be used for it: some log a wrong key and
return no result.

| `status`        | Meaning                                                                                       |
| --------------- | --------------------------------------------------------------------------------------------- |
| `ok`            | The service accepted the key                                                                  |
| `wrong_key`     | `401`, `403` (and `400` for Spotify, IGDB, Google Books), or the body says so (OMDb, Last.fm) |
| `missing_key`   | No key, or no secret for Spotify and IGDB                                                     |
| `rate_limited`  | `429`, or the quota is used                                                                   |
| `service_error` | Any other error of the service                                                                |
| `unreachable`   | No answer within 10 seconds, or no network                                                    |
| `unsupported`   | A service without a key (Deezer, MusicBrainz, Open Library)                                   |

A new service with a key needs its probe: a test fails while one is missing.

## Analyses

`POST /api/scans` starts an analysis of the source folders; `Scans` runs it as
a task of the event loop, one at a time. The type detector of the desktop home
page (`MediaTypeDetector.detect_sources`) runs in a thread, since it reads the
disk; its groups become the rows of the `rows` table (`drafts_from_report`):

| Kind                     | Rows                                                                           |
| ------------------------ | ------------------------------------------------------------------------------ |
| `movie`, `track`, `book` | One per file                                                                   |
| `game`                   | One per game: the `.cue` and `.bin` of a game are one row (`group_game_files`) |
| `episode`                | One per series, its episodes being its files                                   |
| `album`                  | One per album                                                                  |

Each row has a `key`: the kind and the file, or the kind and the series or the
album (as the detector groups them). A new analysis finds its rows again by
that key: a row found again keeps its search, match and destination, and gets
the files of now (a new episode joins its series). The rows not found again
are deleted. A new row is `pending` until it is searched.

`GET /api/scans/current` answers:

| Field      | Contents                                                                                                                                                                |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scan`     | The last analysis: `id`, `status` (`running`, `done`, `failed`, `interrupted`), `started`, `finished`, `error`, `missing_sources`, `processed`; `null` before the first |
| `counts`   | For each media type (`movies`, `tv`, `music`, `books`, `games`): the rows per status, and `total`                                                                       |
| `to_check` | The files whose type is a guess: `path`, `kind` suggested, its `media_type`, `title`, `reason`                                                                          |
| `covers`   | For each media type, up to 3 posters of the results picked (`poster_path` or `image_url`)                                                                               |
| `sources`  | Each source folder: `path`, the `files` of it waiting (rows and files to check), and whether it is `missing`                                                            |

- A source folder that is gone is skipped and listed in `missing_sources`.
- The files already processed are left out and counted in `scan.processed`
  (see [Files already processed](#files-already-processed)).
- An analysis cut by a restart of the server is `interrupted` at the next start.
- `GET /api/settings/disks` gives the disks of the destination folders, then of
  the source folders (`server/disks.py`): one entry per volume, named after
  its first folder, with its `folders`, `total` and `free` bytes; a missing
  folder is left out. `movie_size` is the average size of the movie files
  waiting (`Scans.movie_size()`), or `null`: the analysis page says how many
  movies of that size the first disk still holds.
- `POST /api/to-check` gives a file to check its type (`kind`: `movie`,
  `episode`, `album`, `track`, `book`, `game`): it becomes a row, or joins its
  series or album. The choice goes into `type_choices`, which the next
  analyses apply before making the rows. A new row is searched at once; when
  that search stops (a key missing or refused, a quota used), the file keeps
  its type, the row stays `pending` and the summary has a `search_error`
  (`{code, service}`).

## Search

After the sort, the analysis searches the rows not searched yet
(`Searcher.search_pending`), with the batch engine of the desktop app
(`BatchMatcher`), kind by kind as the desktop batch pages do (`SEARCHES` in
`search.py`):

| Kind      | Tab      | Searched as             | Read by        | One work when | Language of the settings |
| --------- | -------- | ----------------------- | -------------- | ------------- | ------------------------ |
| `movie`   | `movies` | `ContentType.MOVIE`     | `parse_movie`  |               | Yes (`fr` → `fr-FR`)     |
| `episode` | `tv`     | `ContentType.TV_SERIES` | `parse_series` |               | Yes                      |
| `album`   | `music`  | `ContentType.ALBUM`     | `parse_album`  | `same_album`  | No                       |
| `track`   | `music`  | `ContentType.TRACK`     | `parse_track`  | `same_track`  | No                       |
| `book`    | `books`  | `ContentType.BOOK`      | `parse_book`   | `same_book`   | No                       |
| `game`    | `games`  | `ContentType.GAME`      | `parse_game`   |               | Yes                      |

Each row gets its search text,
year, candidates (5 at most), the candidate selected and its status: `ok`
(Ready), `ambiguous` (Pick one) or `missing`. A row is searched once: a new
analysis only searches the new rows.

- **Series.** A series that is Ready, or picked by hand, gets its details and
  the titles of its episodes (`sok.core.series.fetch_episode_titles`), kept in
  `rows.details`: they name the episodes. A series still to pick gets none, to
  spare the quota.
- **When the search stops.** Without an API for a media type (no TMDB key for
  the videos), with a key refused or a quota used, the rows of that media type
  stop: the other media types, which use other services, are still searched.
  The analysis then ends `failed` with `error: {"code", "service"}`:
  `missing_key`, `key_refused` or `rate_limited`, and the service id of the
  registry (`tmdb`, `google_books`…); `others` lists the services that stopped
  after it. The rows keep what they had; those not searched stay `pending`.
- **Progress.** The analysis publishes `progress` events:
  `{"phase": "detect" | "search", "done", "total"}`; the summary gives the same
  in `scan.progress` while it runs.

### Rows

`GET /api/rows?type=movies` gives the rows of a tab:

| Field                                 | Contents                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`, `media_type`, `kind`, `title`   | The row; `title` is the one of a series or an album                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `query`, `year`, `status`, `selected` | The search                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `candidates`                          | `id`, `title`, `original_title`, `by` (the artist of an album or a track, the authors of a book), `year`, `poster`, `overview` (300 characters), and for a book `publisher` and `isbn` (or `null`) of each result                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `files`                               | `path`, `name` and `new_name` of each file, or `null` before a match: for movies the file name the formats give (`generate_new_filename`); for episodes the series and season folders with that name (`Severance/Season 1/Severance S01E01 Good News About Hell.mkv`, or a season folder that already exists in the destination: `episode_folder`); for the other kinds the path under the destination, as the desktop batches move them (`batch_target`): `Daft Punk - Discovery/01 - One More Time.mp3`, `Frank Herbert/Frank Herbert - Dune (1965)/Frank Herbert - Dune (1965).epub`, `Super Nintendo/Chrono Trigger (USA).smc` |
| `files[].error`                       | Why the last rename left the file: `{"code": "already_exists" or "failed", "message"}`, or `null`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `destination`                         | Index of the destination folder of its type                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `size`                                | The size of its files still there, in bytes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `quality`                             | The quality read from the first file name (`"2160p · x265 · DTS"`), or `null`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `episodes_found`                      | For a series: how many episode titles were found, or `null`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |

`PATCH /api/rows/{id}` with `selected` makes the row Ready, as picking a match
does in the desktop app; for a series, it reads the episodes of the new choice.
`destination` is an index in the destination folders of its type
(`invalid_destination` beyond them).

### Live events

`GET /api/events` is a stream of
[server-sent events](https://developer.mozilla.org/docs/Web/API/Server-sent_events)
(`EventSource` in the browser, with the session cookie). It starts with a
`scan` event holding the summary, then sends each event of the `EventBus` as
it happens, and a comment every 15 seconds so that proxies keep it open. Every
change of an analysis publishes a `scan` event with the new summary, every
change of a rename a `rename` event with `GET /api/renames/current`, and every
check of the automatic sorting a `watch` event with `GET /api/watch`. A listener
that reads too slowly loses its oldest events (100 are kept).

## Renames

`POST /api/renames` with `{"type": "movies"}` renames all the Ready rows of the
tab (status `ok` with a candidate selected); `rows` limits it to some of them,
and the rows not Ready are left out. `Renamer` checks before starting, and
answers `409` with a code:

| Code                                                  | Why                                                                                         |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `nothing_to_rename`                                   | No Ready row among those asked                                                              |
| `no_destination`                                      | The media type has no destination folder                                                    |
| `scan_running`, `already_running`                     | An analysis or a rename runs (`Jobs`); an analysis answers `rename_running` during a rename |
| `different_drives`, `no_hard_links`, `missing_folder` | In link mode: `{"code", "source", "destination"}`, the folders that cannot be linked        |

In link mode, one test link (`can_hard_link`) is made for each drive of the
files and each destination: a pair that fails stops the whole rename before
any file moves. An unknown `type` answers `422`.

The rename then runs in a thread, inside `record()` of `sok.core.history`
with the `History` of the server: one operation for the whole tab. Each
destination folder gets the file operations of the desktop batches, which
apply the file mode, the behavior settings and the subtitles:

| Tab                       | Renamed by                                                                               |
| ------------------------- | ---------------------------------------------------------------------------------------- |
| `movies`                  | `VideoFileOperations.organize_movies_batch`                                              |
| `tv`                      | `VideoFileOperations.organize_files_list`, one series at a time, with its season folders |
| `music`, `books`, `games` | `organize_items_batch` of their file operations (`batch_target`)                         |

With `download_posters`, the posters are saved after (`save_artwork`). The
season folders are named in the language of the settings (`season` of the
translation files, read by `ConfigManager.load_language()`).

At the end, the files renamed leave their row; a row left without files is
deleted. A file skipped (`skip_duplicates`) or failed stays, with its reason in
`rows.errors`. `GET /api/renames/current` gives the last rename: `status`
(`running`, `done`, `failed`, `interrupted`), `progress` (`{"done",
"total"}`, also sent as `progress` events with `"phase": "rename"`), and once
done `result`: `renamed`, `subtitles`, `skipped`, `errors` and the id of the
`operation` in the history.

## Automatic sorting

`Watcher` (`server/watcher.py`) runs as a task of the server from its start.
Every 30 seconds (`TICK`) it looks at the clock; when `auto_sort` is on and
`auto_sort_minutes` have passed since its last check, `check()`:

1. does nothing while an analysis or a rename runs (the next tick tries
   again);
2. lists the files of the source folders with their size and `mtime_ns`
   (`snapshot()`), without hidden files and downloads in progress
   (`PARTIAL_SUFFIXES`: `.part`, `.partial`, `.!qb`, `.!ut`, `.crdownload`,
   `.download`);
3. keeps the **finished** files: those with the same size and date as at the
   check before. The first check after a start, or after the switch is turned
   on, only learns the files;
4. if a finished file is new or changed since the last automatic sorting, and
   not already processed, starts an analysis (`Scans.start(auto=True)`), waits
   for it, then renames, tab by tab, the Ready rows whose files are all
   finished (`Renamer.start(..., auto=True)`).

The analyses and renames have `auto` set (columns of `scans` and `renames`, and
in their summaries). The last run is kept in the `options` table
(`auto_sort_last_run`): `date`, `scan` (its id), `renamed` (files), `errors`
(the code of an analysis that could not start or stopped, such as
`missing_key`, and per tab `{"media_type", "code", ...}` of a rename, such as
`no_destination` or a hard link problem). `GET /api/watch` answers `enabled`,
`minutes`, `last_check` (since the start of the server) and `last_run`; a
`watch` event sends it after each check.

The files seen by the last sorting are kept in memory only: after a restart,
one analysis runs again once the files are finished; it finds the rows it
knows and searches nothing again.

## Notifications

After each rename that moved files, by hand or automatic, the `Renamer` hands
it to the `Notifier` (`server/notify.py`), which sends it in the background to
every target set. A target that fails is logged and leaves the others, and
the rename, as they are.

| Target   | Settings (`notifications` of `PATCH /api/settings`) | Sends                                                                           |
| -------- | --------------------------------------------------- | ------------------------------------------------------------------------------- |
| Discord  | `discord_url` (a webhook of a channel)              | A message in the language of the settings: the tab, the count, 10 names at most |
| Jellyfin | `jellyfin_url`, `jellyfin_key` (an API key)         | `POST /Library/Refresh` with `X-Emby-Token`                                     |
| Plex     | `plex_url`, `plex_token`                            | `GET /library/sections/all/refresh` with `X-Plex-Token`                         |
| Webhook  | `webhook_url`                                       | `POST` of the event as JSON                                                     |
| Script   | `SOK_AFTER_RENAME` only (environment)               | Runs the command, the event as JSON on its standard input                       |

- **The event**: `{"event": "renamed", "date", "media_type", "auto",
"renamed", "files": [{"from", "to"}]}`; a test sends `"event": "test"` with
  no file.
- **Where they are kept**: the `options` table (`notify_<field>`). The URL of
  Discord and of the webhook, the key of Jellyfin and the token of Plex are
  secrets: `GET /api/settings` only says whether they are set. An empty value
  removes a field; an address loses its last `/`.
- **The script** is never set from the interface: a command typed in a web page
  would run anything on the server. `SOK_AFTER_RENAME` is split like a shell
  command line (`shlex`) but run without a shell, with `SOK_EVENT`,
  `SOK_MEDIA_TYPE`, `SOK_RENAMED` and `SOK_AUTO` (`1` or `0`) in its
  environment. It has 300 seconds; a non-zero exit is an error with the last
  line it wrote on its error output. In Docker, the script is a file of a
  mounted volume, run by the user of `PUID`.
- **Testing**: `POST /api/settings/test-notification` with a `target`
  (`discord`, `jellyfin`, `plex`, `webhook`, `script`) answers `{"ok": true,
"error": null}`, or the error: `not_set`, `HTTP 401`, a network error, the
  exit code of the script. An unknown target is `422` `unknown_target`.
- The requests have 15 seconds (`aiohttp`).

## History

`History` (`server/history.py`) is the `HistoryStore` of the desktop app with
another place to keep it: the `history` table of `sok.db` instead of
`history.json`. It only replaces `_load()` and `_save()`; recording a rename
and undoing it are the code of the desktop app, with its rules (never replace
a file, a link or a copy deleted only if it is still the original, the last
100 operations). Each operation is one row, its `position` the order (0 is the
newest), with its `media_type`.

`GET /api/history` lists the operations: `id`, `date`, `kind`, `media_type`,
`undone`, `partly_undone`, `auto` (made by the automatic sorting: the
`renames` row whose result names the operation is automatic), `covers` (up
to 3 posters of the rows it renamed, kept in the result of its rename by
`Renamer`; `[]` before 1.6), and `files`:
`index`, `source`, `target`, `mode`, `undone`, `follows` (the new path of the
video of a subtitle).

`POST /api/history/{id}/undo` undoes the whole operation, or with `{"index"}`
one file and its subtitles. It answers `restored` (the paths put back),
`skipped` (`source`, `target` and `reason`: `missing`, `occupied`, `failed`)
and the `operation`. It waits while a rename runs (`409`
`rename_running`); an unknown id or index answers `404` `unknown_operation`.
An undone file is not a row again until the next analysis finds it.

### Files already processed

With a hard link or a copy, a renamed file stays in the downloads. `History.add`
writes each file of the operation still at its old place into the `processed`
table (`path`, `size`, `mtime_ns`, `target`, `operation_id`, `date`), in the
same transaction as the operation: the history and the files processed never
disagree. A moved file is not kept (nothing is left to hide), nor a subtitle
(the analyses never list them). The table is not limited to the 100 operations
of the history.

An analysis reads the table and leaves out of its rows and of its files to
check every file with the same path, size and date (`Scans._detect`); a file
changed since (another download under the same name) is analyzed again. When
an undo puts a file back, `History._write` deletes its entry in the same
transaction as the operation.

`GET /api/processed` lists them, newest first (`path`, `target`, `size`,
`date`, `operation`): the filter "already processed" of the interface.
`POST /api/processed/forget` with `{"paths"}` deletes entries: the next
analysis takes those files again. Neither starts an analysis.

## Database

`sok.db` is a SQLite file (the `sqlite3` module of Python) in `data_dir()`. Each
entry of `MIGRATIONS` in `db.py` is one version of the schema; `PRAGMA
user_version` says how many are applied, and the missing ones run when the
database opens. A released entry is never changed: a change of the schema is a
new entry.

| Table          | Contents                                                                                                                                                                       |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `account`      | The account: `username`, `password_hash`, `created`                                                                                                                            |
| `sessions`     | The open sessions: `token_hash`, `created`, `expires`                                                                                                                          |
| `folders`      | The folders: `role` (`sources` or a media type), `position`, `path`                                                                                                            |
| `scans`        | The analyses: `started`, `finished`, `status`, `error`, `missing_sources`, `processed`, `auto`                                                                                 |
| `rows`         | The rows of the tabs: `key`, `media_type`, `kind`, `title`, `files`, then the search (`query`, `year`, `candidates`, `selected`, `status`), `destination`, `details`, `errors` |
| `to_check`     | The files to check of the last analysis                                                                                                                                        |
| `type_choices` | The types the user gave to files to check                                                                                                                                      |
| `renames`      | The renames: `media_type`, `started`, `finished`, `status`, `error`, `result`, `auto`                                                                                          |
| `options`      | The settings of the server only, the notification fields and the last automatic sorting: `key`, `value` (JSON)                                                                 |
| `processed`    | The files already processed: `path`, `size`, `mtime_ns`, `target`, `operation_id`, `date`                                                                                      |
| `history`      | The rename history: `id`, `position`, `date`, `kind`, `media_type`, and the `operation` as JSON                                                                                |

`Database.transaction()` runs a block of statements together, under a lock: the
requests of the server share one connection.

## Tests

`tests/server/` tests the API with FastAPI's `TestClient` (httpx2), each test
with a database of its own in `tmp_path`. `tests/server/conftest.py` gives each
test a config folder of its own (`SOK_CONFIG_DIR`), without the `.env` of the
repository or the API key variables: `create_app()` reads the `ConfigManager`,
and must never touch the settings of the developer. `Accounts` takes a `clock`, so the
tests move the time forward instead of waiting 30 seconds or 30 days.
