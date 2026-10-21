# ===----------------------------------------------------------------------=== #
#
# This source file is part of the S.O.K open source project
#
# Copyright (c) 2026 S.O.K Team
# Licensed under the MIT License
#
# See LICENSE for license information
#
# ===----------------------------------------------------------------------=== #
"""
Posters and covers saved next to the organized files.

The names are the ones Plex, Jellyfin and Kodi read:

- a movie: "<file name>-poster.jpg" next to the file, since a movie has no
  folder of its own;
- a series: "poster.jpg" in the series folder;
- an album or a track: "cover.jpg" in the album folder;
- a book: "cover.jpg" in the book folder.

Games get none: RAWG gives a screenshot, not a cover. An image already in
place is kept, and a failed download never stops a rename.

The module has no Qt dependency, so the desktop app and S.O.K Server share
it.
"""

import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

import requests

from sok.media.books.book import Book
from sok.media.music.album import Album
from sok.media.music.track import Track
from sok.media.video.movie import Movie
from sok.media.video.series import Series

logger = logging.getLogger(__name__)

# TMDB gives image paths ("/abc.jpg"), not URLs.
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/original"
DOWNLOAD_TIMEOUT = 15


def image_url(path: Optional[str]) -> Optional[str]:
    """Absolute URL of an image of a search result.

    Args:
        path: The "poster_path" of a result: a URL, or a TMDB path.

    Returns:
        The URL, or None without an image.
    """
    if not path:
        return None
    if path.startswith("//"):
        return f"https:{path}"
    if path.startswith("/"):
        return f"{TMDB_IMAGE_BASE}{path}"
    return path


def _letters(text: str) -> str:
    """Letters and digits of a name, to compare a folder with a title."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]+", "", text.casefold())


def artwork_targets(
    item: Any, moved_files: Iterable[str], dest_path: str
) -> Dict[Path, str]:
    """Where the image of an item goes, for the files just moved.

    Args:
        item: The media item of the files, with its "poster_url".
        moved_files: New paths of its files.
        dest_path: Destination folder of the rename.

    Returns:
        The URL to save at each path; empty without an image or for a game.
    """
    url = image_url(getattr(item, "poster_url", None))
    if not url:
        return {}
    ext = ".png" if urlparse(url).path.lower().endswith(".png") else ".jpg"
    files = [Path(f) for f in moved_files]
    targets: Dict[Path, str] = {}

    if isinstance(item, Movie):
        for file in files:
            targets[file.with_name(f"{file.stem}-poster{ext}")] = url
    elif isinstance(item, Series):
        targets[Path(dest_path, item.get_folder_structure()[0], f"poster{ext}")] = url
    elif isinstance(item, (Album, Track)):
        # The cover of an album only goes to a folder named after it: with
        # a music format such as "{artist}/{title}", the tracks of several
        # albums share one folder.
        album = _letters(item.title if isinstance(item, Album) else item.album)
        for file in files:
            if album and album in _letters(file.parent.name):
                targets[file.parent / f"cover{ext}"] = url
    elif isinstance(item, Book):
        for file in files:
            targets[file.parent / f"cover{ext}"] = url
    return targets


def download_artwork(targets: Dict[Path, str]) -> Dict[str, List[Any]]:
    """Download images, keeping those already in place.

    Args:
        targets: The URL to save at each path (see artwork_targets).

    Returns:
        Report with "saved" (paths), "kept" (paths already there) and
        "errors" ({"file", "error"}).
    """
    report: Dict[str, List[Any]] = {"saved": [], "kept": [], "errors": []}
    for target, url in targets.items():
        if target.exists():
            report["kept"].append(str(target))
            continue
        partial = target.with_name(target.name + ".part")
        try:
            response = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            if not response.headers.get("Content-Type", "").startswith("image/"):
                raise ValueError(f"Not an image: {url}")
            partial.write_bytes(response.content)
            os.replace(partial, target)
            report["saved"].append(str(target))
        except (requests.RequestException, OSError, ValueError) as exc:
            partial.unlink(missing_ok=True)
            logger.warning("Poster download failed for %s: %s", target, exc)
            report["errors"].append({"file": str(target), "error": str(exc)})
    return report


def save_artwork(
    mappings: Iterable[Any], moved: Iterable[Dict[str, str]], dest_path: str
) -> Dict[str, List[Any]]:
    """Download the images of the items of a rename.

    Args:
        mappings: (source file, media item) pairs of the rename.
        moved: The "moved" entries of its report ({"from", "to"}).
        dest_path: Destination folder of the rename.

    Returns:
        The report of download_artwork().
    """
    item_of = {str(source): item for source, item in mappings}
    moved_by_item: Dict[int, List[str]] = {}
    items: Dict[int, Any] = {}
    for entry in moved:
        item = item_of.get(entry["from"])
        if item is None:
            continue
        items[id(item)] = item
        moved_by_item.setdefault(id(item), []).append(entry["to"])

    targets: Dict[Path, str] = {}
    for key, files in moved_by_item.items():
        targets.update(artwork_targets(items[key], files, dest_path))
    return download_artwork(targets)
