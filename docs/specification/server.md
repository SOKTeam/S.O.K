---
title: S.O.K Server
description:
  What S.O.K Server must do, how it is built and in which order, agreed before
  writing its code.
---

S.O.K Server is S.O.K for a NAS or a home server: a Docker image with a web
interface. It reads one or more download folders, finds what each file is, and
proposes the new names in a table, like the batch pages of the desktop app. The
user checks the table and renames, with hard links so that torrents keep
seeding.

This page is the specification agreed on 2026-10-21, before any code. Each
requirement has a status: **planned**, **in place since vX.Y.Z**, or
**dropped**. A pull request that changes a rule changes this page too.

## Scope of the first version

| In the first version                                         | Later                                                     |
| ------------------------------------------------------------ | --------------------------------------------------------- |
| Movies, TV shows, music (albums and tracks), books and games | Watching the folders and sorting on arrival               |
| An "Analyze" button that scans the source folders            | Webhook or script after sorting (Jellyfin, Plex, Discord) |
| One table per media type, rename all or row by row           | Several user accounts                                     |
| Hard link, copy or move                                      | Docker Hub (only GitHub Container Registry at first)      |
| History with undo                                            |                                                           |
| The 8 languages of the desktop app                           |                                                           |

## Deployment

**In place since v1.5.0** ([Docker image](/server/overview/#docker-image)).

- Image `ghcr.io/sokteam/sok-server`, tags `latest`, `X.Y.Z` and `X.Y`, for
  `linux/amd64` and `linux/arm64`. Same version number as the desktop app.
- Volumes are free: the user mounts the folders they want (`/downloads`,
  `/movies`…). `/config` holds the settings, the database, the history and the
  logs.
- The interface listens on port `8080` (`SOK_PORT`). `GET /api/health` answers
  for the Docker health check.
- `PUID` and `PGID` set the user the server runs as, so the files it creates
  belong to the user of the NAS. `TZ` sets the time zone of the dates shown.
- No API key of the project is in the image: the desktop builds embed some, the
  image never does. TMDB and TVDB therefore need the user's own keys (free).
  Deezer, MusicBrainz and Open Library work without a key.

```yaml title="docker-compose.yml"
services:
  sok-server:
    image: ghcr.io/sokteam/sok-server:latest
    container_name: sok-server
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Paris
      - API_KEY_TMDB_V4=...        # optional: can be typed in the settings
    volumes:
      - /srv/sok/config:/config
      - /mnt/storage:/data         # one parent folder: hard links work inside it
    ports:
      - 8080:8080
    restart: unless-stopped
```

:::caution
A hard link only works inside one mount. `/mnt/dl:/downloads` and
`/mnt/media:/movies` are two mounts: a link between them fails, even on the same
disk. The example mounts the common parent folder once.
:::

## The user's journey

1. **First visit**: a page asks to create the account (user name and password).
2. **Settings**: API keys, the source folders, the destination folders of each
   media type, the file mode, the name formats and the language.
3. **Analyze**: S.O.K scans the source folders, sorts the files by type and
   searches each one. A summary shows the count per type and the files "to
   check", like the drop zone of the desktop home page.
4. **One tab per type** (Movies, TV shows, Music, Books, Games): a row per file,
   or per series or album, which unfolds. Each row has its search text, its list
   of matches and its status (Ready, Pick one, Missing).
5. **Rename**: "Rename Ready" or "Rename selected". The renamed rows leave the
   table.
6. **History**: every rename can be undone, as a whole or file by file.

## Rules

### Accounts

**In place since v1.5.0** ([Login](/server/overview/#login)); the pages of the
interface are planned.

- One account. It is created on the first visit, or with `SOK_USERNAME` and
  `SOK_PASSWORD` (taken only when no account exists yet).
- The password is stored hashed (Argon2) in `/config`. A forgotten password is
  reset by deleting the account file and visiting the page again.
- A session cookie (`HttpOnly`, `SameSite=Strict`) keeps the user logged in for
  30 days. After 5 failed logins, the next attempts wait 30 seconds.
- `SOK_AUTH=none` turns the login off, for a reverse proxy that already asks for
  one (Authelia, Authentik…). The interface then shows a warning banner.

### API keys

**In place since v1.5.0** ([Settings](/server/overview/#settings),
[Testing a key](/server/overview/#testing-a-key)), except the page of the
interface.

- The settings page lists the services like the desktop app, with a "Test"
  button. The keys typed there are encrypted in `/config`.
- An environment variable (`API_KEY_TMDB_V4`, `API_KEY_TVDB`, `API_KEY_OMDB`,
  `API_KEY_RAWG`, `GOOGLE_BOOKS_API_KEY`, `SPOTIFY_CLIENT_ID`…) **wins** over a
  key typed in the settings, and shows there as locked.
- A key is never written to the logs or sent to the browser: the settings only
  show whether a key is set.

### Folders

**In place since v1.5.0** for the settings and the link check
([Link checks](/server/overview/#link-checks)); the choice per row is planned.

- Several source folders, scanned with their subfolders.
- One or more destination folders per media type. With one, it is used for
  every row of that type. With several, each row has a choice, the first folder
  by default.
- When a source and a destination are saved, S.O.K checks that a hard link
  works between them (same device, then a test link). If not, the settings say
  why and how to fix it (mount the common parent folder once), before any
  rename.

### Analysis

**In place since v1.5.0 for the scan and the sort**
([Analyses](/server/overview/#analyses)); the search is planned.

- The files are sorted by `MediaTypeDetector`
  (`sok/file_operations/detection.py`) and searched by `BatchMatcher`
  (`sok/core/batch.py`): the same rules as the desktop app, including the strict
  Ready status and the input patterns of the settings.
- One analysis at a time. Its progress reaches the browser live (server-sent
  events). Closing the tab does not stop it.
- **Files already processed are hidden.** With hard links, a renamed file stays
  in the downloads: S.O.K remembers every file it renamed (path, size, date) and
  leaves it out of the next analyses. A filter shows them again. An undone file
  is no longer "processed".
- The table is kept in the database: reloading the page, opening a second tab
  or restarting the container keeps the analysis and the choices made.
- **A new analysis keeps the choices.** A row found again keeps its search
  text, its match and its destination; a series or an album keeps them when
  episodes or tracks are added. The rows whose files are gone are removed, the
  new files get rows.
- **One row per series**, with its episodes as sub-rows, and one per album; a
  series spread over several folders is one row.
- **The titles of the episodes** are read when a series becomes Ready or is
  picked by hand, one request per season; not for a series still to pick.
- **A missing key or a used quota stops the analysis**, and the summary says so
  ("TMDB key missing"). The files already sorted stay; the search can be run
  again once the key is set.
- **Files to check** (a type that is a guess, such as an `.iso`, a movie or a
  game) are listed in the summary with the type suggested. The user confirms or
  changes it, and the file joins the tab of that type; the next analyses
  remember the choice.
- Until the tabs of music, books and games arrive, their files are counted in
  the summary.

### Renaming

**Planned.**

- File mode, in the settings: **hard link** (default), **copy** or **move**. A
  hard link that fails gives an error on its row; S.O.K never copies instead
  without being told.
- The names follow the output formats of the settings, like the desktop app.
- The behavior settings of the desktop app apply: create missing folders, skip
  duplicates, back up a replaced file, download posters.
- **Subtitles follow their video** (also in the desktop app, see below).

### Subtitles

**In place since v1.5.0, in the shared core: the desktop app has it too**
([Subtitles](/architecture/organizing/#subtitles)).

- A subtitle whose name starts with the name of the video goes with it:
  `Movie.srt`, `Movie.fr.srt`, `Movie.en.forced.srt`, `Movie.en.sdh.srt`.
- It is renamed like the video and keeps what follows the video's name:
  `Dune (2021).fr.srt`.
- Extensions: `.srt`, `.ass`, `.ssa`, `.sub`, `.idx`, `.vtt`.
- A setting turns it off (`subtitles_follow_video`, on by default).
- Undoing the video puts its subtitles back too.
- `.nfo`, `.txt`, images and samples are left where they are.

### History and undo

**Planned, on `sok.core.history`.** The undo of each mode is in place since
v1.5.0 ([File modes](/architecture/organizing/#file-modes)).

- Same rules as the desktop app: undo a whole rename or one file, never replace
  a file, keep the last 100 operations.
- Undoing depends on the mode the file was renamed with:

| Mode      | Undo                                                                                                      |
| --------- | --------------------------------------------------------------------------------------------------------- |
| Move      | The file goes back to its old place                                                                       |
| Hard link | The link is deleted, if it is still the same file as the source; the source and the torrent are untouched |
| Copy      | The copy is deleted, if the source is still there with the same size                                      |

With the source gone, a link or a copy goes back in its place; with another
file there, it stays.

## How it is built

### Code

**Planned.**

```text
src/sok/
├── core/, apis/, file_operations/, config/, media/   shared with the desktop app
├── ui/                                               desktop interface (Qt)
└── server/                                           S.O.K Server (no Qt)
    ├── app.py        FastAPI application, serves web/dist
    ├── api/          routes: auth, settings, scans, rows, renames, history, events
    ├── db.py         SQLite in /config (sqlite3 of the standard library)
    └── jobs.py       analysis and renames in the background (asyncio)
web/                                                  Svelte interface (Vite), built to web/dist
Dockerfile                                            Node build of web/, then Python slim
```

- `pyproject.toml`: PySide6 and pypresence move to a `desktop` extra; a `server`
  extra adds FastAPI, uvicorn and argon2-cffi. The image installs only
  `server`, so it has no Qt.
- The interface texts reuse `src/sok/resources/i18n/*.json`, plus the texts of
  the server. The language follows the browser and can be changed in the
  settings.
- Commit scopes added to `.commitlintrc.json`: `server`, `web`, `docker`.

### Changes in the shared core

**Planned.** Made first, tested with the desktop app:

1. `SOK_CONFIG_DIR`: the folder of the settings, the key, the history and the
   logs (`/config` in the image). Without it, the paths stay those of today
   (in place since v1.5.0).
2. Environment variables win over the keys of the settings when
   `SOK_ENV_KEYS_WIN` is set (the image sets it). The desktop app keeps today's
   order (in place since v1.5.0).
3. A file mode (`move`, `link`, `copy`) in `move_file` and in the history
   (`Move.mode`), with the undo rules above (in place since v1.5.0; the desktop
   app offers it too, `move` by default).
4. Subtitles that follow their video, with their setting (in place since
   v1.5.0).

### API

**Planned.** JSON under `/api`, the session cookie on every call:

| Route                                                         | Does                                                 |
| ------------------------------------------------------------- | ---------------------------------------------------- |
| `GET /api/health`                                             | Health check, without login                          |
| `GET /api/session`                                            | Account, login and `SOK_AUTH` state, without login   |
| `POST /api/setup`, `POST /api/login`, `POST /api/logout`      | Account and session                                  |
| `GET /api/settings`, `PATCH /api/settings`                    | Settings (keys only as "set" or "not set")           |
| `POST /api/settings/test-key`, `POST /api/settings/test-link` | Test a key, test a hard link                         |
| `POST /api/scans`, `GET /api/scans/current`                   | Start an analysis, read its summary                  |
| `POST /api/to-check`                                          | Give a file to check its type                        |
| `GET /api/rows?type=movie`                                    | Rows of a tab                                        |
| `PATCH /api/rows/{id}`                                        | Change the search text, the match or the destination |
| `POST /api/rows/{id}/search`                                  | Search one row again                                 |
| `POST /api/renames`                                           | Rename rows (all Ready, or a list)                   |
| `GET /api/history`, `POST /api/history/{id}/undo`             | History and undo (whole or one file)                 |
| `GET /api/events`                                             | Server-sent events: progress of analyses and renames |

### Delivery

**In place since v1.5.0** for the image; the docs of the user guide are planned.

- `release.yml` builds the image with Docker Buildx (amd64 and arm64) and pushes
  it to GHCR, as a fourth build next to the three desktop packages. `publish`
  waits for it: a published release always has its image.
- The developer docs get a "S.O.K Server" part (running it from source, the API,
  the database), and the user guide of the website a page on installing it.

## Order of the work

Everything ships in one release; the steps are pull requests to `develop`:

1. **Shared core**: config folder, keys from the environment, file modes,
   subtitles (with the desktop setting and the user guide).
2. **Server skeleton**: FastAPI, SQLite, account and login, settings, health
   check, the Docker image and its CI job.
3. **Analysis**: scan, summary, tabs and rows for movies and TV shows, live
   progress.
4. **Music, books and games** in the tabs.
5. **Renaming**: file modes, link test, already processed files, history and
   undo.
6. **Languages, documentation, website**, then the release.

## Open points

Defaults chosen in this page, to confirm or change during the review:

- Port `8080`, sessions of 30 days, 30 seconds after 5 failed logins.
- One analysis at a time.
- Rows kept until they are renamed or a new analysis replaces them.
