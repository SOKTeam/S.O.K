---
title: Building the app
description:
  Compile S.O.K with Nuitka into the Windows installer, the macOS disk image and
  the Linux AppImages.
---

`scripts/build_sok.py` compiles S.O.K with [Nuitka](https://nuitka.net) for the
system it runs on. Each system builds its own package: there is no
cross-compilation.

## Before building

```sh
uv sync --extra build
```

The build copies the API keys of `.env` into the app, encrypted: only the names
declared in the `Constants` class of `src/sok/core/constants.py` are kept.
Without `.env` the build stops, because the app would ship without its keys. For
a test build, pass `--allow-missing-keys`.

The version comes from `pyproject.toml`. Never change it by hand: releases set
it with `scripts/bump_version.py`.

## Windows

```sh
uv run python scripts/build_sok.py
```

The program is built in `dist/main.dist/` (`SOK.exe` and its files). Then
compile `packaging/windows/installation.iss` with
[Inno Setup](https://jrsoftware.org/isinfo.php): it reads the version from
`SOK.exe` and writes `dist/SOK_Setup_v<version>.exe`.

## macOS

On a Mac with Apple Silicon:

```sh
uv run python scripts/build_sok.py
```

The script builds `dist/S.O.K.app` (arm64, signed ad hoc, as the project has no
Apple Developer ID) and packages it into `dist/SOK_macOS_v<version>.dmg` with
dmgbuild (layout in `packaging/macos/dmg_settings.py`).

:::caution
Check macOS interface changes in a built app, not only from source:
the compiled app is linked with a newer macOS SDK, and macOS changes some
behaviors depending on it.
:::

`scripts/make_macos_assets.py` redraws the app icon and the disk image
background after a change to the logo or the colors.

## Linux

The AppImages are built in AlmaLinux containers, so they run on the oldest glibc
that PySide6 supports for each processor:

| AppImage | Container                 | Runs on                                               |
| -------- | ------------------------- | ----------------------------------------------------- |
| x86_64   | AlmaLinux 9 (glibc 2.34)  | Ubuntu 22.04, Debian 12, Fedora 35, RHEL 9 and newer  |
| aarch64  | AlmaLinux 10 (glibc 2.39) | Ubuntu 24.04, Debian 13, Fedora 40, RHEL 10 and newer |

From the repository root, with Docker:

```sh
docker run --rm --platform linux/amd64 -v "$PWD":/src -w /src \
    almalinux:9 bash packaging/linux/build_appimage.sh
docker run --rm --platform linux/arm64 -v "$PWD":/src -w /src \
    almalinux:10 bash packaging/linux/build_appimage.sh
```

Each run writes `dist/SOK_Linux_v<version>_<arch>.AppImage`. Building the other
processor's AppImage goes through emulation and is much slower. Extra arguments
go to `build_sok.py`, for example `--allow-missing-keys`.

:::caution
`build_sok.py` empties `dist/` before building. Move the packages you
want to keep first.
:::

## Releases

Releases are made by [semantic-release](https://semantic-release.gitbook.io)
when `develop` is merged into `main`: it computes the version from the commit
messages, updates
[`CHANGELOG.md`](https://github.com/SOKTeam/S.O.K/blob/main/CHANGELOG.md) and
the version files, and creates the GitHub release as a **draft**. `release.yml`
then calls `build-windows.yml`, `build-macos.yml` and `build-linux.yml`, which
build the Windows installer, the macOS disk image and both AppImages on GitHub
runners and attach them to the draft, and `build-docker.yml`, which pushes the
S.O.K Server image (see [Docker image](/server/overview/#docker-image)).

When the four builds succeed, the `publish` job publishes the release: only
then do the apps offer the update and the website show the downloads. If a
build fails, the release stays a draft: fix the build, re-run the failed job,
and `publish` runs. The notes of the draft can be edited meanwhile.

`publish` then updates the website, which shows the downloads of the latest
release when it is built:

- Changes of the website for a version wait on the branch `release/vX.Y.Z` of
  [SOKTeam/site](https://github.com/SOKTeam/site), made from its `master`.
  `publish` fast-forwards `master` to it and deletes it; Vercel then deploys
  `master`. This needs the `SITE_TOKEN` secret: a fine-grained token with
  _Contents: read and write_ on SOKTeam/site.
- Without that branch, `publish` calls the Vercel deploy hook of the website
  (`SITE_DEPLOY_HOOK` secret), which rebuilds `master` as it is, with the new
  downloads.
- If `master` moved since the branch was made, the branch is left for a merge by
  hand (a warning in the run) and the deploy hook is called.
- Before `publish`, the `demo` job builds the demo of S.O.K Server from the
  version (`npm run build:demo`) and puts it in `public/demo` on that branch,
  which it makes from `master` when there is none (see
  [Demo](/server/overview/#the-web-project)). It needs `SITE_TOKEN` too; if it
  fails, the release goes on with the demo of before. Its data are **not**
  recorded by the release: run `scripts/record_demo.py` by hand when the API
  or the interface changes what the demo reads.

Without the secrets, this step does nothing.

The desktop workflows write `.env` from the `SOK_ENV` repository secret, which
holds the contents of that file: without it the builds stop. The image never
gets it. Each workflow can also be run
by hand from the Actions tab, on any branch: the package is then kept as an
artifact of the run instead of being attached to a release.
