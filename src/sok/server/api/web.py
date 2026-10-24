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
"""The interface: the files of web/dist, built by Vite.

Every path that is not a file of the build, nor under /api, answers
index.html: the interface reads the address and shows its page. The files
of assets/ have a hash in their name, so the browser keeps them; index.html
is asked again each time, so that an update reaches the browser.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

# web/dist of the repository: src/sok/server/api/web.py is five levels down.
DEFAULT_WEB_DIR = Path(__file__).resolve().parents[4] / "web" / "dist"


def web_dir() -> Optional[Path]:
    """The folder of the built interface (SOK_WEB_DIR, else web/dist of the
    repository), or None when it is not built."""
    folder = Path(os.environ.get("SOK_WEB_DIR") or DEFAULT_WEB_DIR)
    return folder if (folder / "index.html").is_file() else None


def router(folder: Path) -> APIRouter:
    """The routes that serve the interface built in folder."""
    folder = folder.resolve()
    web = APIRouter()

    @web.get("/{path:path}", include_in_schema=False)
    def page(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
        file = (folder / path).resolve()
        if path and file.is_relative_to(folder) and file.is_file():
            cache = (
                "public, max-age=31536000, immutable"
                if path.startswith("assets/")
                else "no-cache"
            )
            return FileResponse(file, headers={"Cache-Control": cache})
        return FileResponse(
            folder / "index.html", headers={"Cache-Control": "no-cache"}
        )

    return web
