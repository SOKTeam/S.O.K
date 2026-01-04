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

import os
import sys
import platform
import subprocess
import shutil
from cryptography.fernet import Fernet
from pathlib import Path


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
                    encrypted_val = f_cipher.encrypt(v.strip().encode()).decode()
                    f.write(f"    {k.strip()} = {encrypted_val!r}\n")

        f.write("\n    @classmethod\n")
        f.write("    def get(cls, attr):\n")
        f.write("        val = getattr(cls, attr, None)\n")
        f.write("        if val and attr != '_K':\n")
        f.write("            return Fernet(cls._K).decrypt(val.encode()).decode()\n")
        f.write("        return None\n")

    return True


def build():
    """Build S.O.K executable using Nuitka."""
    SCRIPT_DIR = Path(__file__).resolve().parent
    ROOT_DIR = SCRIPT_DIR.parent
    os_name = platform.system().lower()

    print(f"\n--- S.O.K. NUITKA COMPILER v1.0.0 | OS: {os_name.upper()} ---")

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

    print(f"\n>>> [3/3] SUCCESS: Build completed in {dist_dir}")


if __name__ == "__main__":
    build()
