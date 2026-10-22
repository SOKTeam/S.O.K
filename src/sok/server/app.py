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
"""The FastAPI application of S.O.K Server, and its entry point (sok-server).

The database is sok.db in data_dir() (SOK_CONFIG_DIR, /config in the
image). The server listens on SOK_HOST (0.0.0.0) and SOK_PORT (8080).
"""

import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI

from sok.__version__ import __version__
from sok.config.config_manager import data_dir, get_config_manager, log_dir
from sok.core.history import LINK
from sok.server.api import auth, events, health, renames, rows, scans, settings
from sok.server.auth import Accounts, auth_disabled
from sok.server.db import Database
from sok.server.events import EventBus
from sok.server.history import History
from sok.server.jobs import Jobs
from sok.server.renames import Renamer
from sok.server.scans import Scans
from sok.server.search import Searcher
from sok.server.settings import Settings

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8080


def create_app(folder: Optional[Path] = None) -> FastAPI:
    """Create the application.

    Args:
        folder: Folder of the database; data_dir() by default.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = Database(Path(folder or data_dir()) / "sok.db")
        app.state.db = db
        app.state.accounts = Accounts(db)
        config = get_config_manager()
        if db.created:
            # The server links by default, so that torrents keep seeding.
            config.set("file_mode", LINK)
        app.state.config = config
        app.state.settings = Settings(db, config)
        app.state.events = EventBus()
        app.state.searcher = Searcher(db, config, app.state.settings)
        app.state.jobs = Jobs()
        app.state.history = History(db)
        app.state.scans = Scans(
            db,
            app.state.settings,
            app.state.events,
            app.state.searcher,
            app.state.jobs,
        )
        app.state.renamer = Renamer(
            db,
            config,
            app.state.events,
            app.state.searcher,
            app.state.history,
            app.state.jobs,
        )
        if app.state.accounts.create_from_env():
            logger.info("Account created from SOK_USERNAME")
        if auth_disabled():
            logger.warning("SOK_AUTH=none: the login is turned off")
        try:
            yield
        finally:
            db.close()

    app = FastAPI(
        title="S.O.K Server",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(settings.router)
    app.include_router(scans.router)
    app.include_router(rows.router)
    app.include_router(renames.router)
    app.include_router(events.router)
    return app


def configure_logging() -> None:
    """Log to the console and to logs/sok.log of the config folder."""
    folder = log_dir()
    folder.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        folder / "sok.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    logging.basicConfig(
        level=os.getenv("SOK_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[file_handler, logging.StreamHandler()],
    )


def main() -> None:
    """Run the server (the sok-server command, and the Docker image)."""
    import uvicorn

    configure_logging()
    uvicorn.run(
        create_app(),
        host=os.environ.get("SOK_HOST", "0.0.0.0"),
        port=int(os.environ.get("SOK_PORT", DEFAULT_PORT)),
        log_config=None,
    )


if __name__ == "__main__":
    main()
