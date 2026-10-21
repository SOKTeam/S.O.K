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

| Function      | Reads                                                                    |
| ------------- | ------------------------------------------------------------------------ |
| `parse_movie` | Title and year: `Heat (1995).mkv`, `heat.1995.1080p.mkv`                 |
| `parse_book`  | Title and author; the year is ignored (it is often the edition's)        |
| `parse_game`  | Title without the dump tags: `[SNES] Chrono Trigger (USA) (Rev 1).smc`   |
| `parse_track` | The tags of the file first, then `Artist - Title`; the album of its tags |

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
the title must be unique among the results. Two results can count as one work:
the editions of a book (`same_book`), or a track on an album and on a
compilation or a live album (`same_track`). A track found only on compilations,
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
| Book  | `Author/Author - Title (Year)/Author - Title (Year).ext`                                                                                             |
| Game  | One file: `Platform/Title (tags of the dump).ext`. Several files: `Platform/Title (Year)/`, with their names kept, since a .cue names its .bin files |
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
  destination. Each name comes from the episode format setting, with the episode
  title of the series: `{title} S{season}E{episode} {episode_title}`.
- **Albums**: each track is named from the music format, with the artist, album
  and year of the album found online, and the title and number of its tags (or
  of its file name).

## From the home page

Files dropped on the home page are sorted by `MediaTypeDetector`
(`sok/file_operations/detection.py`), run by `DetectionWorker`. It gives one
group per batch page (movies, tracks, books, games) and one group per series and
per album. Files whose type is a guess (an `.iso` can be a movie or a game) are
listed for the user to confirm. Opening a group calls `MainWindow._open_group`,
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

The "Behavior" settings apply to every page:

| Setting                | Effect                                                                            |
| ---------------------- | --------------------------------------------------------------------------------- |
| `create_folders`       | Creates the missing folders. When off, a file whose folder is missing is an error |
| `skip_duplicates`      | Leaves a file in place when its new name already exists                           |
| `backup_before_rename` | Keeps the replaced file as `<name>.backup`                                        |
| `log_operations`       | Writes each move to the log                                                       |
| `download_posters`     | Saves the poster or cover of each item next to its files (see below)              |

Files are moved by `move_file` (`sok.file_operations.base_operations`). It
replaces an existing file of the same name, unless `skip_duplicates` is on. A
move to another drive is a copy followed by a deletion. If the move fails, the
backup it made is put back.

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

:::caution
There is no undo yet: once moved, a file stays where it is. Test with copies of
your files.
:::

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
