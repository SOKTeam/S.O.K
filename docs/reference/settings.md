---
title: Settings and environment
description:
  Every key of config.json, the environment variables S.O.K reads, where the API
  keys come from and how they are protected.
---

## The settings file

The settings are saved in `config.json`: `data/config.json` in the repository
when S.O.K runs from source, and the folders given in
[Set up](/getting-started/setup/#run-the-app) for the installed app. The file is
written each time a setting changes (`ConfigManager.set()`), and created with
the default values when it is missing.

| Key                                                                                        | Default                                       | In the settings    | Effect                                                                                                                                                           |
| ------------------------------------------------------------------------------------------ | --------------------------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `language`                                                                                 | `en`                                          | Appearance         | Language of the interface and of the folder names (`Season`, `Saison`…)                                                                                          |
| `theme`                                                                                    | `system` on macOS, `dark` elsewhere           | Appearance         | `light`, `dark`, or `system` to follow the system                                                                                                                |
| `use_system_accent`                                                                        | `false`                                       | Appearance (macOS) | Uses the accent color of macOS instead of orange                                                                                                                 |
| `default_video_path`, `default_music_path`, `default_books_path`, `default_games_path`     | empty                                         | Default Folders    | Destination folder filled in on the pages of that type                                                                                                           |
| `movie_format`                                                                             | `{title} ({year})`                            | Output Formats     | Name of a movie. Also `{quality}`                                                                                                                                |
| `video_format`                                                                             | `{title} S{season}E{episode} {episode_title}` | Output Formats     | Name of an episode. Also `{season_num}`, `{episode_num}` (not padded)                                                                                            |
| `music_format`                                                                             | `{artist} - {album}/{track} - {title}`        | Output Formats     | Folders and name of a track: one part per folder, the name last. Also `{year}`                                                                                   |
| `book_format`                                                                              | `{author} - {title} ({year})`                 | Output Formats     | Name of a book found online. Also `{series}`, `{series_number}` (from the file name)                                                                             |
| `game_format`                                                                              | `{title} {tags}`                              | Output Formats     | Name of a one-file game found online. Also `{year}`, `{platform}`; `{tags}` are those of the dump                                                                |
| `input_patterns`                                                                           | `{}`                                          | Input Formats      | Patterns of the file names, per kind: `episode`, `movie`, `music`, `book`, `game` ([Reading the file names](/architecture/organizing/#2-reading-the-file-names)) |
| `create_folders`                                                                           | `true`                                        | Behavior           | Creates the missing folders; when off, a file whose folder is missing is an error                                                                                |
| `backup_before_rename`                                                                     | `true`                                        | Behavior           | Keeps a replaced file as `<name>.backup`                                                                                                                         |
| `skip_duplicates`                                                                          | `true`                                        | Behavior           | Leaves a file in place when its new name already exists                                                                                                          |
| `log_operations`                                                                           | `true`                                        | Behavior           | Writes each move to the log                                                                                                                                      |
| `download_posters`                                                                         | `false`                                       | Behavior           | Saves the poster or cover of each item after a rename ([Posters and covers](/architecture/organizing/#posters-and-covers))                                       |
| `preferred_api_video`, `preferred_api_music`, `preferred_api_books`, `preferred_api_games` | `tmdb`, `deezer`, `google_books`, `igdb`      | Preferred API      | Service searched for that type, when its key is available ([Choosing the API](/architecture/overview/#choosing-the-api))                                         |
| `check_updates`                                                                            | `true`                                        | About              | Looks for a new release at startup ([Updates](/architecture/updates/))                                                                                           |
| `use_discord_rpc`                                                                          | `false`                                       | About              | Shows the activity of S.O.K in Discord                                                                                                                           |
| `api_key_*`, `spotify_*`, `igdb_*`, `google_books_api_key`, `client_id_discord`            | empty                                         | API Keys           | The user's own keys (see below)                                                                                                                                  |

In the formats, a value that a file does not have is left out with the text
around it: without a year, `{title} ({year})` gives `Title`. Folder and file
names then lose the characters that Windows does not accept:
`< > : " / \ | ? *`.

Read a setting with `get_config_manager().get(key, default)`, and change it with
`set(key, value)`, which saves the file.

## Where an API key comes from

For each service, `get()` returns the first key it finds:

1. **The user's key**, typed in Settings › API Keys and saved in `config.json`.
2. **The key of the build**, in the `Constants` class (`sok/core/constants.py`)
   of a compiled app. See [Building](/guides/building/#before-building).
3. **The environment**: the variables of `.env` at the repository root, or of
   the shell.

The API Keys section only shows the user's keys (`get_user_value()`), never
those of the build or of `.env`.

### Protection

- **In `config.json`**, the user's keys are encrypted with
  [Fernet](https://cryptography.io/en/latest/fernet/) and saved as `ENC:…`. The
  encryption key is `data/.local.key`, next to `config.json`, created at the
  first start (hidden on Windows). A `config.json` copied to another computer
  without its `.local.key` loses its keys: S.O.K logs the failure and leaves
  them empty.
- **In a build**, the keys of `.env` are encrypted into `Constants` by
  `scripts/build_sok.py`, and decrypted when they are read (`Constants.get()`).
  This keeps them out of a plain reading of the executable; it does not make
  them secret from someone who takes the app apart.

### Debugger check

At startup, `sok.core.security.check_security()` quits S.O.K, on Windows only,
when a native debugger is attached (Visual Studio, WinDbg, x64dbg…). This also
applies when S.O.K runs from source. Python debuggers, such as the ones of VS
Code and PyCharm, are not native debuggers and are not detected.

## Environment variables

| Variable                                                       | Effect                                                  |
| -------------------------------------------------------------- | ------------------------------------------------------- |
| `API_KEY_TMDB_V4`, `API_KEY_TVDB`, `API_KEY_OMDB`              | Keys of the video services (TMDB: the v4 read token)    |
| `API_KEY_LASTFM`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` | Keys of the music services                              |
| `GOOGLE_BOOKS_API_KEY`                                         | Key of Google Books                                     |
| `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`, `API_KEY_RAWG`         | Keys of the game services                               |
| `API_KEY_FANART`                                               | Key of Fanart.tv                                        |
| `CLIENT_ID_DISCORD`                                            | Application of the Discord activity                     |
| `SOK_LOG_LEVEL`                                                | Level of the log: `DEBUG`, `INFO` (default), `WARNING`… |

`.env.example` lists the keys with the page where each one is created. Deezer,
MusicBrainz and Open Library need none.

The installed app also uses variables set by the system: `APPIMAGE` and `APPDIR`
(Linux, set by the AppImage), `XDG_DATA_HOME` and `XDG_STATE_HOME` (Linux
folders).
