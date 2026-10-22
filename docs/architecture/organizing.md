---
title: The path of a rename
description:
  How S.O.K finds the online item of each file, decides whether it can be
  renamed as is, and moves it into the library.
---

Renaming happens on two kinds of pages:

- **Batch pages**, where every file (or group of files) gets its own online
  item: Movies, Books, Games and the Tracks tab of Music.
- **One-item pages**, where all the files belong to one item chosen by the user:
  TV shows (one series) and the Albums tab of Music (one album).

The batch engine, `sok.core.batch`, has no Qt dependency: S.O.K Server will use
it as it is.

## Batch pages

| Page   | One row is                           | Organized by                                |
| ------ | ------------------------------------ | ------------------------------------------- |
| Movies | a video file                         | `VideoFileOperations.organize_movies_batch` |
| Books  | a book file                          | `BookFileOperations.organize_items_batch`   |
| Games  | a ROM, or the .cue/.bin files of one | `GameFileOperations.organize_items_batch`   |
| Tracks | an audio file                        | `MusicFileOperations.organize_items_batch`  |

Each page is a subclass of `BatchPage` (`sok/ui/pages/batch_page.py`), which
holds the table, the workers and the buttons. A subclass only sets class
attributes (media type, content type, how to read a file name, how rows are
grouped) and a few texts.

### 1. Adding files

Files dropped on the page, picked in the file dialog or sent from the home page
(`BatchPage.load_files`) go to the table, `MediaBatchTable`. Its `group_files`
function makes the rows: one per file by default, one per game for games
(`group_game_files`: a .cue, .m3u or .gdi takes the files it lists). Files that
are already in the table are skipped.

### 2. Reading the file names

The `parse` function of the page reads the files of a row and returns a
`ParsedName`: the text to search, and what the results are compared with.

| Function       | Reads                                                                                                                                                                                                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `parse_movie`  | Title and year: `Heat (1995).mkv`, `heat.1995.1080p.mkv`                                                                                                                                                                                                                        |
| `parse_book`   | Title and author; the year is ignored (it is often the edition's)                                                                                                                                                                                                               |
| `parse_game`   | Title without the dump tags: `[SNES] Chrono Trigger (USA) (Rev 1).smc`                                                                                                                                                                                                          |
| `parse_track`  | The tags of the file first, then `Artist - Title`; the album of its tags                                                                                                                                                                                                        |
| `parse_series` | The series title the type detector gives the episodes (file name, or the folders above a season folder), and a year at its end: `Doctor.Who.2005.S01E01.mkv` → Doctor Who, 2005. Used by S.O.K Server, with `ContentType.TV_SERIES`                                             |
| `parse_album`  | The album and artist most tracks give in their tags (the album artist first), and their year; without tags, the folder: `Daft Punk - Discovery (2001)`, `Radiohead - 1997 - OK Computer`, above a `CD1` folder. Used by S.O.K Server, with `ContentType.ALBUM` and `same_album` |

Each of them calls `extract_info_from_filename` of the file operations, which
tries the **input patterns** of the settings first (`sok.core.name_patterns`),
then its own rules (`_parse_filename`). A pattern uses the variables of the
name formats: `{artist} - {year} - {album} - {track} - {title}`. In a pattern,
spaces, dots and underscores are the same separator, the spaces around a dash
are optional, `{year}` takes four digits, the numbers take digits, and
`{ignore}` skips any part of the name. The info of a name read by a pattern has
a `pattern` key. The tags of a track still come before its name.

### 3. Searching

`BatchSearchWorker` runs `BatchMatcher.match_all` in a background thread. The
matcher searches 4 rows at a time with the API selected for the media type,
keeps the first 5 results of each, and gives each row a status with `evaluate`.

A failed search makes its row "Missing", except two errors that would fail every
row the same way and stop the batch: `APIAuthenticationError` (missing or wrong
key) and `APIRateLimitError` (quota used). The page then shows a message written
by `sok.ui.errors.error_message`.

### 4. The status of a row

`evaluate` follows a strict rule: a row is only **Ready** when S.O.K is sure.

| Status   | When                                                                                                                                      |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Ready    | One result has the title of the file (or its original title) and, when the file gives them, its year, its author or artist, and its album |
| Pick one | Results were found, but none or several match exactly. The most likely one is selected                                                    |
| Missing  | The search found nothing                                                                                                                  |

Titles are compared after `normalize_title`: accents, case, punctuation and
spaces are ignored, and "&" counts as "and". Without a year in the file name,
the title must be unique among the results; a year that none of the results
with that title gives (Deezer gives none for albums) is left out. An author or
artist must be the same, except a last name alone ("Herbert", "F. Herbert"),
which matches "Frank Herbert": "Daft Punk" is not "Data Punk". Two results can
count as one work: the editions of a book (`same_book`), the versions of an
album with the same title and artist (`same_album`), or a track on an album and
on a compilation or a live album (`same_track`). A track found only on compilations,
live or remix releases is never Ready (`on_other_release`): the album it came
out on is still unknown.

The user can change the selected result of a row, or type another search (the
row is searched again with that text as its title).

### 5. Renaming

"Rename all" only takes the Ready rows. The page builds a `sok.media` item for
each one (`create_media_item`) and starts `BatchOrganizeWorker` with
`(file, item)` pairs. The organize method of the file operations moves each file
where `batch_target(item, file, alone)` says:

| Type  | Destination                                                                                                                                          |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Movie | `Title (Year).ext`, from the movie format setting                                                                                                    |
| Book  | `Author/Author - Title (Year)/`, then the name from the book format setting (`Author - Title (Year).ext` by default)                                 |
| Game  | One file: `Platform/`, then the name from the game format setting. Several files: `Platform/Title (Year)/`, names kept (a .cue names its .bin files) |
| Track | The music format setting, `{artist} - {album}/{track} - {title}` by default                                                                          |

The platform of a game comes from a `[SNES]` tag, the extension or the folder
name (`GameFileOperations.detect_platform`).

## One-item pages

On TV shows and Albums, the user searches and selects one series or one album
(`SearchWorker`, then `DetailsWorker` for the episodes or the tracks). The page
builds the item, and `OrganizeWorker` calls `organize_files_list` of the file
operations:

- **TV shows** (`VideoFileOperations.organize_files_list`): the files go to
  `Series/Season N/`, or to a season folder that already exists in the
  destination (`episode_folder()`, which S.O.K Server also uses for its
  preview). Each name comes from the episode format setting, with the episode
  title of the series: `{title} S{season}E{episode} {episode_title}`. The season
  folders and the episode titles come from `sok.core.series` (no Qt, shared with
  S.O.K Server): `season_folders(details, season_word)` names each season
  ("Season 2", or "Season 2 - The Return" when the season has a name of its
  own), and `fetch_episode_titles()` reads the episodes of each season
  (`S01E01` → title); a season that fails is skipped.
- **Albums**: each track is named from the music format, with the artist, album
  and year of the album found online, and the title and number of its tags (or
  of its file name).

## From the home page

Files dropped on the home page are sorted by `MediaTypeDetector`
(`sok/file_operations/detection.py`), run by `DetectionWorker`. It gives one
group per batch page (movies, tracks, books, games) and one group per series and
per album. Files whose type is a guess (an `.iso` can be a movie or a game) are
listed for the user to confirm. A video read by an episode pattern of the
settings is an episode, one read by a movie pattern is a movie. Opening a group calls `MainWindow._open_group`,
which shows the page of its type and gives it the files (`load_files` on a batch
page).

## Names and safety settings

The new names go through `format_name` (`sok.core.utils`), which removes the
characters that Windows does not accept in file names: `< > : " / \ | ? *`.

The formats can be changed in the settings:

| Setting        | Default                                       |
| -------------- | --------------------------------------------- |
| `movie_format` | `{title} ({year})`                            |
| `video_format` | `{title} S{season}E{episode} {episode_title}` |
| `music_format` | `{artist} - {album}/{track} - {title}`        |
| `book_format`  | `{author} - {title} ({year})`                 |
| `game_format`  | `{title} {tags}`                              |

The "Behavior" settings apply to every page:

| Setting                  | Effect                                                                            |
| ------------------------ | --------------------------------------------------------------------------------- |
| `file_mode`              | `move`, `link` (hard link) or `copy`: how the files reach their new place         |
| `create_folders`         | Creates the missing folders. When off, a file whose folder is missing is an error |
| `skip_duplicates`        | Leaves a file in place when its new name already exists                           |
| `backup_before_rename`   | Keeps the replaced file as `<name>.backup`                                        |
| `log_operations`         | Writes each move to the log                                                       |
| `download_posters`       | Saves the poster or cover of each item next to its files (see below)              |
| `subtitles_follow_video` | Moves the subtitles of a video with it (see below)                                |

Files are moved by `move_file` (`sok.file_operations.base_operations`). It
replaces an existing file of the same name, unless `skip_duplicates` is on. A
move to another drive is a copy followed by a deletion. If the move fails, the
backup it made is put back.

### File modes

`move_file(..., mode=...)` takes the `file_mode` of the settings (`MOVE`,
`LINK` or `COPY`, from `sok.core.history`):

| Mode   | The source         | The new file                                            |
| ------ | ------------------ | ------------------------------------------------------- |
| `move` | Leaves its place   | Is the file itself                                      |
| `link` | Stays, for seeding | A hard link: the same data under a second name, no copy |
| `copy` | Stays              | A copy                                                  |

A link or a copy is made under a temporary name next to the destination, then
put in place, so a failure leaves no half file. A hard link only works on one
drive (and one Docker mount), on a disk that supports it (not FAT, exFAT or most
network shares). When it fails, `move_file` raises `HardLinkError`: the file is
an error of the report, never copied instead. A file already at its destination
(the same file) is left as it is.

Before a rename in `link` mode, the pages call `hard_link_blocked`
(`sok/ui/controllers/file_mode.py`): `can_hard_link` makes one test link per
drive of the files, and a failure stops the rename with a message that says how
to fix it.

### Posters and covers

With `download_posters` on, the rename workers call
`sok.file_operations.artwork.save_artwork` after the moves. The image of each
item (`poster_url`, kept by `create_media_item` from the search result) is saved
where Plex, Jellyfin and Kodi look for it:

| Type         | Image                                              |
| ------------ | -------------------------------------------------- |
| Movie        | `Title (Year)-poster.jpg` next to the file         |
| Series       | `poster.jpg` in the series folder                  |
| Album, track | `cover.jpg` in the album folder, when there is one |
| Book         | `cover.jpg` in the book folder                     |

An image already in place is kept, and a failed download is only logged. Games
get none: RAWG gives screenshots, not covers. Like the batch engine, the module
has no Qt dependency.

### Subtitles

With `subtitles_follow_video` on (the default), each video moved by
`VideoFileOperations` takes its subtitles along
(`sok.file_operations.subtitles`, no Qt dependency). A subtitle is a `.srt`,
`.ass`, `.ssa`, `.sub`, `.idx` or `.vtt` file next to the video whose name
starts with the video's name and a dot. It gets the new name of the video and
keeps the rest of its own:

| Before             | After                |
| ------------------ | -------------------- |
| `dune.2021.mkv`    | `Dune (2021).mkv`    |
| `dune.2021.srt`    | `Dune (2021).srt`    |
| `dune.2021.fr.srt` | `Dune (2021).fr.srt` |
| `dune.2021.nfo`    | Left where it is     |

When two videos of a folder can claim a subtitle (`Movie.mkv` and
`Movie.Part2.mkv` for `Movie.Part2.srt`), the longest name wins.
`skip_duplicates` and `backup_before_rename` apply to subtitles as to videos.
The report lists them in `"subtitles"`, apart from `"moved"`, so the counts
and the posters stay those of the videos; a skipped or failed subtitle joins
`"skipped"` or `"errors"`. The rename workers pass their number on as
`"subtitles"`: the end message adds "With 3 subtitle(s).", and the History page
counts them apart and shows each one under its video.

:::tip
A rename can be undone: see [Rename history](#rename-history) below.
:::

## Rename history

Each rename can be undone, from the message shown at its end ("Undo rename") or
from the History page. `sok/core/history.py` keeps the history, without Qt.

**Recording.** `BatchOrganizeWorker` and `OrganizeWorker` run the rename and the
poster downloads inside `history.record(kind)`. While it runs, three functions
report what they do to the active journal (`current_journal()`):

| Function                           | Reports                                                 |
| ---------------------------------- | ------------------------------------------------------- |
| `move_file` (`base_operations`)    | Each file moved, and the `.backup` of a replaced file   |
| `make_folders` (`base_operations`) | Each folder created (use it instead of `os.makedirs`)   |
| `save_artwork` (`artwork`)         | Each poster or cover saved, and the files it belongs to |

At the end, a journal with moves becomes an `Operation` of `get_history()`,
saved in `history.json` next to `config.json`. The last 100 operations are
kept. The worker's report gives its id in `"operation"`.

**Undoing.** `HistoryStore.undo(operation_id, index=None)` puts back every file
of the operation, or the one at `index` with the files that follow it (its
subtitles, moved with `move_file(..., follows=video)` and saved as
`Move.follows`), last moved first. It never replaces a file: a file no longer
at its new place (`MISSING`) or whose old place is taken (`OCCUPIED`) is skipped
and listed in the `UndoReport`. A file renamed in `link` or `copy` mode
(`Move.mode`) is deleted when its source is still the original (the same file
for a link, the same size for a copy); with the source gone, it goes back in its
place, and with another file there, it stays (`OCCUPIED`). The `.backup` of a
replaced file is put back. A poster is deleted once all its files are back. The
folders the rename created are removed when they are empty (or hold only
`.DS_Store`, `Thumbs.db` or `desktop.ini`). The UI runs it in `UndoWorker`.

Tests get a history of their own (`tests/conftest.py`), never the user's one.

## Adding a batch page

1. Write a `parse_*` function in `sok.core.batch` that returns a `ParsedName`,
   and a `same_*` function if several results can be one work.
2. Give the file operations of the type a `batch_target` if its files do not
   simply go into `item.get_folder_structure()` under `generate_new_filename()`.
   Most types get `organize_items_batch` from `FileListOrganizerMixin`
   (`sok/file_operations/organize.py`).
3. Subclass `BatchPage`: set `media_type`, `content_type`, `factory_type` and
   `parse`, and write `make_ops`, `organize_method` and the texts.
4. Add the page to the window and its kind to `PAGE_BY_KIND` in
   `main_window.py`, so that the home page can open it.
