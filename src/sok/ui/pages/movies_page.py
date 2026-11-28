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
"""Page for batch-renaming movie files, each with its own TMDB movie."""

from typing import Any, Callable, Dict

from sok.core.batch import parse_movie
from sok.core.interfaces import ContentType, MediaType
from sok.file_operations import VideoFileOperations
from sok.ui.i18n import tr
from sok.ui.components.scene import Shape
from sok.ui.pages.batch_page import BatchPage


class MoviesPage(BatchPage):
    """Page for batch movie renaming."""

    kind = "movies"
    scene_shape = Shape.POSTER
    show_quality = True
    default_path_type = "video"
    media_type = MediaType.VIDEO
    content_type = ContentType.MOVIE
    factory_type = "movie"
    parse = staticmethod(parse_movie)

    def make_ops(self) -> VideoFileOperations:
        return VideoFileOperations()

    def organize_method(self) -> Callable[..., Dict[str, Any]]:
        return self._ops.organize_movies_batch

    def page_title(self) -> str:
        return tr("movies", "Movies")

    def nothing_ready_text(self) -> str:
        return tr("no_movies_ready", "No movies are ready to rename.")
