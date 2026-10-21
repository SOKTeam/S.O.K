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
login, the health check and the settings. The test of a key, the analysis, the
renames, the web interface and the Docker image follow.
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

## Code

| File                     | Contents                                                                     |
| ------------------------ | ---------------------------------------------------------------------------- |
| `server/app.py`          | `create_app(folder)`, the logging and `main()`                               |
| `server/db.py`           | `Database`: `sok.db` and its migrations                                      |
| `server/auth.py`         | `Accounts`: the account, the password check, the sessions; `auth_disabled()` |
| `server/api/auth.py`     | The routes of the account and the session, and `require_login`               |
| `server/api/health.py`   | `GET /api/health`                                                            |
| `server/settings.py`     | `Settings`: the settings, the keys and the folders; `check_link()`           |
| `server/api/settings.py` | The routes of the settings                                                   |

`create_app()` opens the database when the application starts (its lifespan),
creates the account from `SOK_USERNAME` and `SOK_PASSWORD` if needed, and puts
the `Database`, the `Accounts`, the `ConfigManager` and the `Settings` in
`app.state`. The routes read them from the request. A new database is a new
installation: `create_app()` then sets the file mode to `link`, the default of
the server (the desktop app moves).

## API

JSON under `/api`. FastAPI's own `/docs` page is turned off.

| Route                          | Login | Does                                                                        |
| ------------------------------ | ----- | --------------------------------------------------------------------------- |
| `GET /api/health`              | No    | `{"status": "ok", "version", "db"}`, for the health check of Docker         |
| `GET /api/session`             | No    | `auth` (`login` or `none`), `account`, `logged_in`, `username`              |
| `POST /api/setup`              | No    | Creates the account (`username`, `password`) and logs in; once only (`409`) |
| `POST /api/login`              | No    | Opens a session (`401` for a wrong login, `429` while waiting)              |
| `POST /api/logout`             | Yes   | Closes the session                                                          |
| `GET /api/settings`            | Yes   | The settings, the keys, the folders and the link checks (see below)         |
| `PATCH /api/settings`          | Yes   | Changes some of them (`settings`, `keys`, `folders`); answers like `GET`    |
| `POST /api/settings/test-link` | Yes   | `{source, destination}`: whether a hard link works between them             |

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

## Database

`sok.db` is a SQLite file (the `sqlite3` module of Python) in `data_dir()`. Each
entry of `MIGRATIONS` in `db.py` is one version of the schema; `PRAGMA
user_version` says how many are applied, and the missing ones run when the
database opens. A released entry is never changed: a change of the schema is a
new entry.

| Table      | Contents                                                            |
| ---------- | ------------------------------------------------------------------- |
| `account`  | The account: `username`, `password_hash`, `created`                 |
| `sessions` | The open sessions: `token_hash`, `created`, `expires`               |
| `folders`  | The folders: `role` (`sources` or a media type), `position`, `path` |

`Database.transaction()` runs a block of statements together, under a lock: the
requests of the server share one connection.

## Tests

`tests/server/` tests the API with FastAPI's `TestClient` (httpx2), each test
with a database of its own in `tmp_path`. `tests/server/conftest.py` gives each
test a config folder of its own (`SOK_CONFIG_DIR`), without the `.env` of the
repository or the API key variables: `create_app()` reads the `ConfigManager`,
and must never touch the settings of the developer. `Accounts` takes a `clock`, so the
tests move the time forward instead of waiting 30 seconds or 30 days.
