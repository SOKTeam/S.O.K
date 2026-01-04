"""Upload binaries to latest GitHub release."""

import sys
import os
from pathlib import Path


def get_version():
    """Read version from pyproject.toml."""
    try:
        import tomli
    except ImportError:
        print("❌ tomli not installed. Run: pip install tomli")
        sys.exit(1)

    with open("pyproject.toml", "rb") as f:
        return tomli.load(f)["project"]["version"]


def get_github_token():
    """Get GitHub token from environment or .env file."""
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        try:
            with open(".env") as f:
                for line in f:
                    if line.startswith("GITHUB_TOKEN="):
                        token = line.split("=", 1)[1].strip()
                        break
        except FileNotFoundError:
            pass

    if not token:
        print("❌ GITHUB_TOKEN not found!")
        print("Set it as environment variable or in .env file")
        sys.exit(1)

    return token


def upload_asset(release_id, filepath, token, repo):
    """Upload a file to GitHub release."""
    try:
        import requests
    except ImportError:
        print("❌ requests not installed. Run: pip install requests")
        sys.exit(1)

    filename = Path(filepath).name

    print(f"📤 Uploading {filename}...")

    url = f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets"

    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/octet-stream",
    }

    params = {"name": filename}

    with open(filepath, "rb") as f:
        response = requests.post(url, headers=headers, params=params, data=f)

    if response.status_code == 201:
        print(f"✅ Uploaded: {filename}")
        return True
    else:
        print(f"❌ Failed to upload {filename}: {response.status_code}")
        print(response.json())
        return False


def get_latest_release(token, repo):
    """Get the latest release ID."""
    try:
        import requests
    except ImportError:
        print("❌ requests not installed. Run: pip install requests")
        sys.exit(1)

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {"Authorization": f"token {token}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data["id"], data["tag_name"]
    else:
        print(f"❌ Failed to get latest release: {response.status_code}")
        sys.exit(1)


def main():
    """Main upload function."""
    REPO = "SOKTeam/S.O.K"

    token = get_github_token()
    version = get_version()

    print(f"🚀 Uploading binaries for v{version}...")

    release_id, tag_name = get_latest_release(token, REPO)
    print(f"📦 Found release: {tag_name} (ID: {release_id})")

    dist_dir = Path("dist")
    binaries = list(dist_dir.glob("S.O.K-*"))

    if not binaries:
        print("❌ No binaries found in dist/")
        print("Run 'python scripts/build_all.py' first")
        sys.exit(1)

    print(f"Found {len(binaries)} file(s) to upload:")
    for binary in binaries:
        print(f"  - {binary.name}")

    success = 0
    for binary in binaries:
        if upload_asset(release_id, binary, token, REPO):
            success += 1

    print(f"\n✅ Successfully uploaded {success}/{len(binaries)} files")


if __name__ == "__main__":
    main()
