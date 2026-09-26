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
Build script using Nuitka to compile S.O.K into a standalone executable.
Handles secure injection of environment variables and Nuitka configuration.
"""

import argparse
import ast
import os
import sys
import platform
import subprocess
import shutil
from cryptography.fernet import Fernet
from pathlib import Path

from bump_version import read_version


def require_env_file(root_dir: Path, allow_missing: bool) -> bool:
    """Check that the .env file holding the API keys exists.

    Without it the build would silently ship an app with no API keys.

    Args:
        root_dir: Repository root, where .env lives.
        allow_missing: Build without keys instead of failing (test builds).

    Returns:
        True if .env exists.

    Raises:
        SystemExit: If .env is missing and allow_missing is False.
    """
    if (root_dir / ".env").exists():
        return True
    if not allow_missing:
        sys.exit(
            "!!! No .env file: the app would be built without its API keys.\n"
            "Copy .env to the repository root (see .env.example), or pass "
            "--allow-missing-keys for a test build."
        )
    print("!!! WARNING: no .env file, building WITHOUT API keys.")
    return False


def declared_constants(source: str) -> set[str]:
    """List the values the app can read from its Constants class.

    Args:
        source: Source code of sok/core/constants.py.

    Returns:
        Names assigned in the Constants class body, except the master key.
    """
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef) and node.name == "Constants":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    targets = stmt.targets
                elif isinstance(stmt, ast.AnnAssign):
                    targets = [stmt.target]
                else:
                    continue
                names.update(t.id for t in targets if isinstance(t, ast.Name))
    names.discard("_K")
    return names


def inject_env_vars(src_sok_dir, root_dir):
    """Inject encrypted API keys from .env into constants.py."""
    core_dir = src_sok_dir / "core"
    constants_path = core_dir / "constants.py"
    env_path = root_dir / ".env"

    if not env_path.exists():
        return False

    print(">>> [1/3] Injecting API keys into Constants class...")

    master_key = Fernet.generate_key()
    f_cipher = Fernet(master_key)

    original = (
        constants_path.read_text(encoding="utf-8") if constants_path.exists() else ""
    )
    allowed = declared_constants(original)
    split_token = "class Constants"
    header = original.split(split_token, 1)[0] if split_token in original else original

    with open(constants_path, "w", encoding="utf-8") as f:
        if header:
            f.write(header.rstrip() + "\n\n")
        else:
            f.write("from cryptography.fernet import Fernet\n\n")

        f.write("class Constants:\n")
        f.write(f"    _K = {master_key!r}\n")  # La clé est stockée dans le binaire

        with open(env_path, "r", encoding="utf-8") as f_env:
            for line in f_env:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    # Only what the app reads: tooling secrets stay out of
                    # the binary.
                    if k.strip() not in allowed:
                        print(f"    Skipping {k.strip()}: not used by the app")
                        continue
                    encrypted_val = f_cipher.encrypt(v.strip().encode()).decode()
                    f.write(f"    {k.strip()} = {encrypted_val!r}\n")

        f.write("\n    @classmethod\n")
        f.write("    def get(cls, attr):\n")
        f.write("        val = getattr(cls, attr, None)\n")
        f.write("        if val and attr != '_K':\n")
        f.write("            return Fernet(cls._K).decrypt(val.encode()).decode()\n")
        f.write("        return None\n")

    return True


MACOS_BUNDLE_ID = "com.sokteam.sok"


def finalize_app_bundle(dist_dir: Path) -> Path:
    """Give the Nuitka app bundle its final layout and signature.

    Nuitka puts the resources in Contents/MacOS, where codesign treats
    each file as code and stores its signature in extended attributes,
    which copies drop. In Contents/Resources they are sealed by the bundle
    signature instead.

    Args:
        dist_dir: Nuitka output folder containing main.app.

    Returns:
        Path to S.O.K.app.
    """
    app = dist_dir / "S.O.K.app"
    (dist_dir / "main.app").rename(app)
    shutil.rmtree(dist_dir / "main.dist", ignore_errors=True)

    contents = app / "Contents"
    (contents / "MacOS" / "resources").rename(contents / "Resources" / "resources")

    subprocess.run(["xattr", "-cr", str(app)], check=True)
    subprocess.run(
        [
            "codesign",
            "--force",
            "--deep",
            "--sign",
            "-",
            "--identifier",
            MACOS_BUNDLE_ID,
            str(app),
        ],
        check=True,
    )
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    return app


def make_dmg(app: Path, version: str) -> Path:
    """Package the macOS app bundle into a drag-to-install disk image.

    The window layout (background, icon positions) is described in
    packaging/macos/dmg_settings.py and written by dmgbuild, without
    scripting the Finder.

    Args:
        app: Signed S.O.K.app bundle.
        version: Application version, used in the file name.

    Returns:
        Path to the created .dmg file.
    """
    import dmgbuild

    packaging = Path(__file__).resolve().parent.parent / "packaging" / "macos"
    dmg = app.parent / f"SOK_macOS_v{version}.dmg"
    print(f">>> Creating {dmg.name}...")
    dmgbuild.build_dmg(
        str(dmg),
        "S.O.K",
        settings_file=str(packaging / "dmg_settings.py"),
        defines={
            "app": str(app),
            "background": str(packaging / "dmg_background.tiff"),
        },
    )
    return dmg


def build(allow_missing_keys: bool = False):
    """Build S.O.K executable using Nuitka.

    Args:
        allow_missing_keys: Build even if .env (the API keys) is missing.
    """
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT_DIR = SCRIPT_DIR.parent
    os_name = platform.system().lower()

    version = read_version("pyproject.toml")
    print(f"\n--- S.O.K. v{version} NUITKA BUILD | OS: {os_name.upper()} ---")
    require_env_file(ROOT_DIR, allow_missing_keys)

    build_dir = ROOT_DIR / "build" / "nuitka_work"
    dist_dir = ROOT_DIR / "dist"

    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    build_dir.mkdir(parents=True)

    temp_src = build_dir / "src"
    shutil.copytree(ROOT_DIR / "src", temp_src)

    inject_env_vars(temp_src / "sok", ROOT_DIR)

    print(">>> [2/3] C++ compilation in progress (may take several minutes)...")

    nuitka_cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--output-filename=SOK.exe",
        "--enable-plugin=pyside6",
        "--include-package=sok",
        "--follow-imports",
        "--include-data-dir="
        + str(ROOT_DIR / "src" / "sok" / "resources")
        + "=resources",
        "--include-module=sok.core.constants",
        f"--windows-icon-from-ico={ROOT_DIR}/src/sok/resources/assets/logo.ico",
        "--output-dir=" + str(dist_dir),
        "--no-pyi-file",
        "--remove-output",
        "--python-flag=-O",
        str(temp_src / "sok" / "main.py"),
    ]

    if os_name == "windows":
        nuitka_cmd.append("--windows-console-mode=disable")
        # Version info shown in the .exe properties (Details tab). The
        # installer reads ProductVersion from it (see
        # packaging/windows/installation.iss).
        nuitka_cmd.extend(
            [
                "--product-name=S.O.K",
                f"--product-version={version}",
                f"--file-version={version}",
                "--file-description=Storage Organisation Kit",
                "--company-name=S.O.K Team",
                "--copyright=© 2026 S.O.K Team",
            ]
        )

    if os_name == "darwin":
        # Apple Silicon .app bundle, ad-hoc signed (no Apple Developer ID).
        nuitka_cmd = [
            arg
            for arg in nuitka_cmd
            if not arg.startswith(("--output-filename=", "--windows-icon-from-ico="))
        ]
        nuitka_cmd[-1:-1] = [
            "--output-filename=SOK",
            "--macos-create-app-bundle",
            "--macos-target-arch=arm64",
            "--macos-app-mode=gui",
            "--macos-app-name=S.O.K",
            f"--macos-app-version={version}",
            f"--macos-signed-app-name={MACOS_BUNDLE_ID}",
            f"--macos-app-icon={ROOT_DIR}/src/sok/resources/assets/logo.icns",
        ]

    current_env = os.environ.copy()
    current_env["PYTHONPATH"] = (
        str(temp_src) + os.pathsep + current_env.get("PYTHONPATH", "")
    )

    try:
        subprocess.run(nuitka_cmd, check=True, cwd=ROOT_DIR, env=current_env)
    except subprocess.CalledProcessError as e:
        print("\n!!! NUITKA ERROR !!!")
        print("Check the output above for details.")
        raise e

    if os_name == "darwin":
        app = finalize_app_bundle(dist_dir)
        make_dmg(app, version)

    print(f"\n>>> [3/3] SUCCESS: Build completed in {dist_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build S.O.K with Nuitka.")
    parser.add_argument(
        "--allow-missing-keys",
        action="store_true",
        help="build even without a .env file (the app then has no API keys)",
    )
    build(parser.parse_args().allow_missing_keys)
