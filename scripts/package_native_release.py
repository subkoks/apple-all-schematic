#!/usr/bin/env python3
"""Prepare verified, versioned native release assets without publishing to GitHub."""

import argparse
import hashlib
import json
import plistlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILD_INPUTS = [
    "native",
    "src",
    "scripts",
    "args",
    "context",
    "pyproject.toml",
    "LICENSE",
    "docs/releases",
]


def prepare(app: Path, architecture: str, dmg: Path | None = None) -> Path:
    release = json.loads((REPO / "native/release.json").read_text())
    if not all(
        isinstance(release.get(key), str) for key in ("version", "build", "release_version")
    ):
        raise ValueError("Release metadata must contain string version, build and release_version")
    if (
        not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-rc\.[0-9]+)?", release["release_version"])
        or release["release_version"].split("-", 1)[0] != release["version"]
        or not re.fullmatch(r"[0-9]+", release["build"])
    ):
        raise ValueError("Invalid native release version or build")
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    if (
        info["CFBundleShortVersionString"] != release["version"]
        or info["CFBundleVersion"] != release["build"]
    ):
        raise ValueError("The app does not match native/release.json. Rebuild it first.")
    version = release["release_version"]
    stage = Path(tempfile.mkdtemp(prefix="native-release-", dir=REPO / "build"))
    package = stage / "release"
    package.mkdir()
    basename = f"BoardVault-{version}-macos-{architecture}"
    archive = package / f"{basename}.zip"
    subprocess.run(
        ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app), str(archive)], check=True
    )
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None:
            raise ValueError("Corrupt release archive")
        if plistlib.loads(zipped.read("BoardVault.app/Contents/Info.plist")) != info:
            raise ValueError("Release archive version mismatch")
        for name in zipped.namelist():
            parts = Path(name).parts
            if ".." in parts or any(
                part.startswith(".env") or ".session" in part for part in parts
            ):
                raise ValueError("Unexpected sensitive or unsafe archive entry")
    # Verify the delivered archive, including permissions and symbolic links.
    with tempfile.TemporaryDirectory(prefix="unpacked-", dir=stage) as unpacked:
        subprocess.run(["ditto", "-x", "-k", str(archive), unpacked], check=True)
        subprocess.run(
            ["codesign", "--verify", "--deep", "--strict", str(Path(unpacked) / "BoardVault.app")],
            check=True,
        )
    assets = [archive]
    if dmg is not None:
        mount = stage / "mounted-image"
        mount.mkdir()
        subprocess.run(
            ["hdiutil", "attach", "-readonly", "-nobrowse", "-mountpoint", str(mount), str(dmg)],
            check=True,
            capture_output=True,
        )
        try:
            image_app = mount / "BoardVault.app"
            if plistlib.loads((image_app / "Contents/Info.plist").read_bytes()) != info:
                raise ValueError("Disk image version mismatch")
            for relative in ("Contents/MacOS/BoardVault", "Contents/_CodeSignature/CodeResources"):
                if (image_app / relative).read_bytes() != (app / relative).read_bytes():
                    raise ValueError("Disk image contains a different app build")
            subprocess.run(
                ["codesign", "--verify", "--deep", "--strict", str(image_app)], check=True
            )
        finally:
            subprocess.run(["hdiutil", "detach", str(mount)], check=True, capture_output=True)
        image = package / f"{basename}.dmg"
        shutil.copy2(dmg, image)
        assets.append(image)
    shutil.copy2(REPO / "docs/releases" / f"{version}.md", package / "RELEASE_NOTES.md")
    checksums = [
        {
            "file": asset.name,
            "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
            "bytes": asset.stat().st_size,
        }
        for asset in assets
    ]
    (package / "SHA256SUMS").write_text(
        "".join(f"{item['sha256']}  {item['file']}\n" for item in checksums)
    )
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    modified = subprocess.check_output(
        ["git", "status", "--porcelain", "--", *BUILD_INPUTS], cwd=REPO, text=True
    )
    manifest = {
        **release,
        "architecture": architecture,
        "minimum_macos": "13.0",
        "source_commit": revision,
        "modified_build_inputs": bool(modified.strip()),
        "signing": "ad-hoc",
        "notarized": False,
        "assets": checksums,
    }
    (package / "release.json").write_text(json.dumps(manifest, indent=2) + "\n")
    destination = REPO / "dist/releases" / f"{version}-{architecture}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.rename(stage / "previous-release")
    package.rename(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=REPO / "dist/native/BoardVault.app")
    parser.add_argument("--arch", choices=["x86_64", "universal2"], required=True)
    parser.add_argument("--dmg", type=Path)
    args = parser.parse_args()
    print(f"Release assets: {prepare(args.app.resolve(), args.arch, args.dmg)}")


if __name__ == "__main__":
    main()
