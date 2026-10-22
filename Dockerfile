# S.O.K Server: the web version of S.O.K, for a NAS or a home server.
#
#   docker build -t sok-server .
#   docker run -p 8080:8080 -v ./config:/config -v /mnt/storage:/data sok-server
#
# Only the "server" extra is installed: no Qt. The image holds no API key of
# the project (see .dockerignore): the users give their own. Node only builds
# the interface (web/dist); the image does not keep it.

FROM ghcr.io/astral-sh/uv:0.9.21 AS uv

# The interface is the same files on every platform: built once, on the
# platform of the build machine.
FROM --platform=$BUILDPLATFORM node:24-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.13-slim-trixie

# tzdata for TZ; util-linux gives setpriv, which drops to PUID:PGID.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata util-linux \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# The dependencies first: this layer only changes with uv.lock.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev --extra server \
    && rm /usr/local/bin/uv

# The code runs from src/, without the desktop interface.
COPY src/ ./src/
COPY --from=web /web/dist ./web/dist
COPY packaging/docker/entrypoint.sh /usr/local/bin/sok-entrypoint

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    SOK_CONFIG_DIR=/config \
    SOK_ENV_KEYS_WIN=1 \
    SOK_HOST=0.0.0.0 \
    SOK_PORT=8080 \
    PUID=1000 \
    PGID=1000

VOLUME /config
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"SOK_PORT\"]}/api/health', timeout=4)"

LABEL org.opencontainers.image.title="S.O.K Server" \
      org.opencontainers.image.description="Organizes movies, TV shows, music, books and games from a web interface" \
      org.opencontainers.image.source="https://github.com/SOKTeam/S.O.K" \
      org.opencontainers.image.licenses="MIT"

ENTRYPOINT ["sok-entrypoint"]
CMD ["python", "-m", "sok.server.app"]
