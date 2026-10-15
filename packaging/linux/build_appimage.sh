#!/usr/bin/env bash
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
#
# Build the Linux AppImage inside an AlmaLinux 9 container.
#
# AlmaLinux 9 has glibc 2.34, the oldest PySide6 6.10 supports: the AppImage
# then runs on every distribution at least as recent (RHEL 9 and its
# rebuilds, Ubuntu 22.04, Debian 12, Fedora 35, openSUSE Tumbleweed, Arch...).
#
# Used by .github/workflows/build-linux.yml. Locally, from the repository root:
#
#   docker run --rm --platform linux/amd64 -v "$PWD":/src -w /src \
#       almalinux:9 bash packaging/linux/build_appimage.sh
#
# Extra arguments go to scripts/build_sok.py (e.g. --allow-missing-keys).

set -euo pipefail

APPIMAGETOOL_VERSION=1.9.1

echo ">>> Installing build tools and the libraries Qt loads at run time..."
dnf install -y -q epel-release
dnf install -y -q --setopt=install_weak_deps=False \
    gcc gcc-c++ patchelf ccache file findutils git \
    fontconfig freetype dbus-libs glib2 libxkbcommon libxkbcommon-x11 \
    libxcb xcb-util-cursor xcb-util-image xcb-util-keysyms \
    xcb-util-renderutil xcb-util-wm libX11-xcb \
    mesa-libGL mesa-libEGL libglvnd-glx libglvnd-egl \
    libwayland-client libwayland-cursor libwayland-egl

echo ">>> Installing uv and Python..."
if ! command -v uv >/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
# Keep the container environment apart from the host .venv (bind mount).
export UV_PROJECT_ENVIRONMENT=/opt/sok-venv
uv sync --frozen --extra build

echo ">>> Installing appimagetool ${APPIMAGETOOL_VERSION}..."
arch="$(uname -m)"
tool=/opt/appimagetool
curl -LsSf -o "$tool" \
    "https://github.com/AppImage/appimagetool/releases/download/${APPIMAGETOOL_VERSION}/appimagetool-${arch}.AppImage"
chmod +x "$tool"
# Containers have no FUSE: run appimagetool from its extracted files.
export APPIMAGE_EXTRACT_AND_RUN=1
export APPIMAGETOOL="$tool"

uv run --frozen --no-sync python scripts/build_sok.py "$@"
