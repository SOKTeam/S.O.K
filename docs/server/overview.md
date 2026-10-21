---
title: S.O.K Server
description: Running S.O.K Server from source, its JSON API, its database and its login.
---

S.O.K Server is the web version of S.O.K, for a NAS or a home server: a FastAPI
application in `sok/server/`, on the same core as the desktop app and without
Qt. What it must do is in the [specification](/specification/server/); this
part describes what is built.

:::note
The server is being built. In place today: the database, the account, the
login, the health check, the settings, the test of a key, the Docker image and
the analyses with the search of every media type. The renames and the web
interface follow.
:::

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
| `SOK_AUTH=none`                | Turns the login off, behind a reverse proxy that asks for one          |
| `SOK_LOG_LEVEL`                | Level of the log: `DEBUG`, `INFO` (default)…                           |

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
| `server/settings.py`                          | `Settings`: the settings, the keys and the folders; `check_link()`                   |
| `server/api/settings.py`                      | The routes of the settings                                                           |
| `server/scans.py`                             | `Scans`: the analyses, the rows, the files to check                                  |
| `server/events.py`                            | `EventBus`: the events sent to the browsers                                          |
| `server/api/scans.py`, `server/api/events.py` | The routes of the analyses and `GET /api/events`                                     |
| `server/search.py`, `server/api/rows.py`      | `Searcher`: the search of the rows, their changes and what the tabs show; its routes |

`create_app()` opens the database when the application starts (its lifespan),
creates the account from `SOK_USERNAME` and `SOK_PASSWORD` if needed, and puts
the `Database`, the `Accounts`, the `ConfigManager` and the `Settings` in
`app.state`. The routes read them from the request. A new database is a new
installation: `create_app()` then sets the file mode to `link`, the default of
the server (the desktop app moves).

## API

JSON under `/api`. FastAPI's own `/docs` page is turned off.

| Route                          | Login | Does                                                                                           |
| ------------------------------ | ----- | ---------------------------------------------------------------------------------------------- |
| `GET /api/health`              | No    | `{"status": "ok", "version", "db"}`, for the health check of Docker                            |
| `GET /api/session`             | No    | `auth` (`login` or `none`), `account`, `logged_in`, `username`                                 |
| `POST /api/setup`              | No    | Creates the account (`username`, `password`) and logs in; once only (`409`)                    |
| `POST /api/login`              | No    | Opens a session (`401` for a wrong login, `429` while waiting)                                 |
| `POST /api/logout`             | Yes   | Closes the session                                                                             |
| `GET /api/settings`            | Yes   | The settings, the keys, the folders and the link checks (see below)                            |
| `PATCH /api/settings`          | Yes   | Changes some of them (`settings`, `keys`, `folders`); answers like `GET`                       |
| `POST /api/settings/test-link` | Yes   | `{source, destination}`: whether a hard link works between them                                |
| `POST /api/settings/test-key`  | Yes   | `{service, key?, secret?}`: whether a key works (see [Testing a key](#testing-a-key))          |
| `POST /api/scans`              | Yes   | Starts an analysis (`202`, `{"id"}`); `409` with `already_running` or `no_sources`             |
| `GET /api/scans/current`       | Yes   | The last analysis, the counts of the rows and the files to check (see [Analyses](#analyses))   |
| `POST /api/to-check`           | Yes   | `{path, kind}`: gives a file to check its type; answers the summary                            |
| `GET /api/events`              | Yes   | Server-sent events (see [Live events](#live-events))                                           |
| `GET /api/rows?type=movies`    | Yes   | The rows of a tab (see [Rows](#rows))                                                          |
| `GET /api/rows/{id}`           | Yes   | One row                                                                                        |
| `PATCH /api/rows/{id}`         | Yes   | `{selected?, destination?}`: picks a candidate (the row is then Ready) or a destination folder |
| `POST /api/rows/{id}/search`   | Yes   | `{query?}`: searches the row again, with the text typed; `409` when a key stops it             |

The interface starts with `GET /api/session`: no account → the setup page; an
account and no session → the login page; otherwise the app.

A route that needs a session declares `dependencies=[Depends(require_login)]`;
without one, it answers `401` with `"not_logged_in"`. The errors give a code in
`detail` (`account_exists`, `invalid_account`, `wrong_login`,
`too_many_attempts`, `not_logged_in`) that the interface translates.

## Login

- **The account**: one row of the `account` table. The user name is not empty,
  the password has at least 8 characters (`MIN_PASSWORD_LENGTH`). The password
  is hashed with Argon2 (`argon2-cffi`), and hashed again at the next login when
  the parameters of Argon2 change. A forgotten password: stop the server,
  delete `sok.db`, start it again.
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

| Field         | Contents                                                                                                                     |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `settings`    | `language`, `file_mode`, the behavior switches and the five name formats (`SETTINGS` in `settings.py`)                       |
| `languages`   | The languages of the interface                                                                                               |
| `keys`        | Each service (`service`, `name`, `media_type`, `url` to get a key) and its keys: `{"key", "set", "locked"}`, never the value |
| `folders`     | `sources`, and the destination folders of `movies`, `tv`, `music`, `books`, `games`, in order                                |
| `link_checks` | In `link` mode, one check per source and destination: `ok`, `problem`, `tested`                                              |

- **Where they are kept.** The settings and the keys shared with the desktop
  app stay in `config.json`, through the `ConfigManager`: the core reads them
  there. The folders, which only the server has, are in the `folders` table.
- **Changing them.** `PATCH /api/settings` takes any of `settings`, `keys` and
  `folders`. Everything is checked before anything is saved; the first problem
  answers `422` with `{"code", "item"}` in `detail`: `unknown_setting`,
  `invalid_value`, `unknown_key`, `key_locked`, `unknown_folder_role`,
  `invalid_folder` (not an absolute path to an existing folder, as the server
  sees it).
- **Keys.** An empty value removes a key. A key is `set` when the settings or an
  environment variable give it, and `locked` when an environment variable wins
  over it (`SOK_ENV_KEYS_WIN`, see
  [Where an API key comes from](/reference/settings/#where-an-api-key-comes-from)):
  a locked key cannot be changed. Only the keys that `config.json` can hold are
  listed. After a change of keys, the media manager is built again for the next
  search.
- **Folders.** Each role given replaces its list; paths are normalized and
  duplicates dropped.

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

| Field      | Contents                                                                                                                                                   |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scan`     | The last analysis: `id`, `status` (`running`, `done`, `failed`, `interrupted`), `started`, `finished`, `error`, `missing_sources`; `null` before the first |
| `counts`   | For each media type (`movies`, `tv`, `music`, `books`, `games`): the rows per status, and `total`                                                          |
| `to_check` | The files whose type is a guess: `path`, `kind` suggested, its `media_type`, `title`, `reason`                                                             |

- A source folder that is gone is skipped and listed in `missing_sources`.
- An analysis cut by a restart of the server is `interrupted` at the next start.
- `POST /api/to-check` gives a file to check its type (`kind`: `movie`,
  `episode`, `album`, `track`, `book`, `game`): it becomes a row, or joins its
  series or album. The choice goes into `type_choices`, which the next
  analyses apply before making the rows.

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

| Field                                 | Contents                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`, `media_type`, `kind`, `title`   | The row; `title` is the one of a series or an album                                                                                                                                                                                                                                                                                                                                                                                    |
| `query`, `year`, `status`, `selected` | The search                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `candidates`                          | `id`, `title`, `original_title`, `year`, `poster`, `overview` (300 characters) of each result                                                                                                                                                                                                                                                                                                                                          |
| `files`                               | `path`, `name` and `new_name` of each file, or `null` before a match: for movies and episodes the file name the formats give (`generate_new_filename`); for the other kinds the path under the destination, as the desktop batches move them (`batch_target`): `Daft Punk - Discovery/01 - One More Time.mp3`, `Frank Herbert/Frank Herbert - Dune (1965)/Frank Herbert - Dune (1965).epub`, `Super Nintendo/Chrono Trigger (USA).smc` |
| `destination`                         | Index of the destination folder of its type                                                                                                                                                                                                                                                                                                                                                                                            |
| `episodes_found`                      | For a series: how many episode titles were found, or `null`                                                                                                                                                                                                                                                                                                                                                                            |

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
change of an analysis publishes a `scan` event with the new summary. A listener
that reads too slowly loses its oldest events (100 are kept).

## Database

`sok.db` is a SQLite file (the `sqlite3` module of Python) in `data_dir()`. Each
entry of `MIGRATIONS` in `db.py` is one version of the schema; `PRAGMA
user_version` says how many are applied, and the missing ones run when the
database opens. A released entry is never changed: a change of the schema is a
new entry.

| Table          | Contents                                                                                                                                                             |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `account`      | The account: `username`, `password_hash`, `created`                                                                                                                  |
| `sessions`     | The open sessions: `token_hash`, `created`, `expires`                                                                                                                |
| `folders`      | The folders: `role` (`sources` or a media type), `position`, `path`                                                                                                  |
| `scans`        | The analyses: `started`, `finished`, `status`, `error`, `missing_sources`                                                                                            |
| `rows`         | The rows of the tabs: `key`, `media_type`, `kind`, `title`, `files`, then the search (`query`, `year`, `candidates`, `selected`, `status`), `destination`, `details` |
| `to_check`     | The files to check of the last analysis                                                                                                                              |
| `type_choices` | The types the user gave to files to check                                                                                                                            |

`Database.transaction()` runs a block of statements together, under a lock: the
requests of the server share one connection.

## Tests

`tests/server/` tests the API with FastAPI's `TestClient` (httpx2), each test
with a database of its own in `tmp_path`. `tests/server/conftest.py` gives each
test a config folder of its own (`SOK_CONFIG_DIR`), without the `.env` of the
repository or the API key variables: `create_app()` reads the `ConfigManager`,
and must never touch the settings of the developer. `Accounts` takes a `clock`, so the
tests move the time forward instead of waiting 30 seconds or 30 days.
