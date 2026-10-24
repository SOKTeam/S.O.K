#!/bin/sh
# Entry point of the S.O.K Server image.
#
# Started as root (the default), it gives /config to PUID:PGID and runs the
# server as that user, so that the files it creates belong to the user of
# the NAS. Started with --user, it runs the server as it is.
set -eu

mkdir -p "$SOK_CONFIG_DIR"

if [ "$(id -u)" = "0" ]; then
    # Only /config: the media folders keep the owners they have.
    chown -R "$PUID:$PGID" "$SOK_CONFIG_DIR"
    export HOME="$SOK_CONFIG_DIR"
    exec setpriv --reuid="$PUID" --regid="$PGID" --clear-groups -- "$@"
fi

exec "$@"
