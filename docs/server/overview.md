---
title: S.O.K Server
description: Running S.O.K Server from source, its JSON API, its database and its login.
---

S.O.K Server is the web version of S.O.K, for a NAS or a home server: a FastAPI
application in `sok/server/`, on the same core as the desktop app and without
Qt. What it must do is in the [specification](/specification/server/); this
part describes what is built.

:::note
The server is being built. In place today: the database, the account, the login
and the health check. The settings, the analysis, the renames, the web interface
and the Docker image follow.
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

| File                   | Contents                                                                     |
| ---------------------- | ---------------------------------------------------------------------------- |
| `server/app.py`        | `create_app(folder)`, the logging and `main()`                               |
| `server/db.py`         | `Database`: `sok.db` and its migrations                                      |
| `server/auth.py`       | `Accounts`: the account, the password check, the sessions; `auth_disabled()` |
| `server/api/auth.py`   | The routes of the account and the session, and `require_login`               |
| `server/api/health.py` | `GET /api/health`                                                            |

`create_app()` opens the database when the application starts (its lifespan),
creates the account from `SOK_USERNAME` and `SOK_PASSWORD` if needed, and puts
the `Database` and the `Accounts` in `app.state`. The routes read them from the
request.

## API

JSON under `/api`. FastAPI's own `/docs` page is turned off.

| Route              | Login | Does                                                                        |
| ------------------ | ----- | --------------------------------------------------------------------------- |
| `GET /api/health`  | No    | `{"status": "ok", "version", "db"}`, for the health check of Docker         |
| `GET /api/session` | No    | `auth` (`login` or `none`), `account`, `logged_in`, `username`              |
| `POST /api/setup`  | No    | Creates the account (`username`, `password`) and logs in; once only (`409`) |
| `POST /api/login`  | No    | Opens a session (`401` for a wrong login, `429` while waiting)              |
| `POST /api/logout` | Yes   | Closes the session                                                          |

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

## Database

`sok.db` is a SQLite file (the `sqlite3` module of Python) in `data_dir()`. Each
entry of `MIGRATIONS` in `db.py` is one version of the schema; `PRAGMA
user_version` says how many are applied, and the missing ones run when the
database opens. A released entry is never changed: a change of the schema is a
new entry.

| Table      | Contents                                              |
| ---------- | ----------------------------------------------------- |
| `account`  | The account: `username`, `password_hash`, `created`   |
| `sessions` | The open sessions: `token_hash`, `created`, `expires` |

`Database.transaction()` runs a block of statements together, under a lock: the
requests of the server share one connection.

## Tests

`tests/server/` tests the API with FastAPI's `TestClient` (httpx2), each test
with a database of its own in `tmp_path`. `Accounts` takes a `clock`, so the
tests move the time forward instead of waiting 30 seconds or 30 days.
