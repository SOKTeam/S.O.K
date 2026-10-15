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
# Build the Linux AppImage of this machine's architecture inside an
# AlmaLinux container.
#
# A binary runs on the glibc it was built with or newer, so each
# architecture is built on the oldest glibc its PySide6 wheels support:
#
#   x86_64   AlmaLinux 9    glibc 2.34   RHEL 9, Ubuntu 22.04, Debian 12,
#                                        Fedora 35 and newer
#   aarch64  AlmaLinux 10   glibc 2.39   RHEL 10, Ubuntu 24.04, Debian 13,
#                                        Fedora 40 and newer
#
# Used by .github/workflows/build-linux.yml. Locally, from the repository root:
#
#   docker run --rm --platform linux/amd64 -v "$PWD":/src -w /src \
#       almalinux:9 bash packaging/linux/build_appimage.sh
#   docker run --rm --platform linux/arm64 -v "$PWD":/src -w /src \
#       almalinux:10 bash packaging/linux/build_appimage.sh
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
tool=/opt/appimagetool.AppImage
curl -LsSf -o "$tool" \
    "https://github.com/AppImage/appimagetool/releases/download/${APPIMAGETOOL_VERSION}/appimagetool-${arch}.AppImage"
chmod +x "$tool"
# Containers have no FUSE, so unpack appimagetool instead of mounting it.
# Clear the AppImage magic bytes first (ELF padding, offset 8): emulated
# runs (Docker on Apple Silicon) refuse to execute the file with them.
printf '\0\0\0' | dd of="$tool" bs=1 seek=8 conv=notrunc status=none
(cd /opt && "$tool" --appimage-extract >/dev/null && mv squashfs-root appimagetool)
export APPIMAGETOOL=/opt/appimagetool/AppRun

uv run --frozen --no-sync python scripts/build_sok.py "$@"
