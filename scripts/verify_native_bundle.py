#!/usr/bin/env python3
"""Reject wrong-architecture or post-Ventura binaries before packaging the DMG."""

import sys
from pathlib import Path

from macholib.mach_o import LC_BUILD_VERSION, LC_LOAD_DYLIB, LC_VERSION_MIN_MACOSX
from macholib.MachO import MachO

MAX_MACOS_VERSION = 13 << 16
ARCHITECTURES = {"x86_64": {0x01000007}, "universal2": {0x01000007, 0x0100000C}}
MACHO_MAGICS = {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}


def verify(app: Path, architecture: str):
    required = ARCHITECTURES[architecture]
    checked = 0
    for path in app.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open("rb") as stream:
            if stream.read(4) not in MACHO_MAGICS:
                continue
        binary = MachO(str(path))
        if not required.issubset({header.header.cputype for header in binary.headers}):
            raise ValueError(f"Wrong architecture: {path.relative_to(app)}")
        for header in binary.headers:
            for command, version, dependency in header.commands:
                if command.cmd == LC_LOAD_DYLIB:
                    link = dependency.rstrip(b"\x00").decode()
                    if link.startswith("/") and not link.startswith(
                        ("/System/Library/", "/usr/lib/")
                    ):
                        raise ValueError(f"External library dependency: {path.relative_to(app)}")
                minimum = None
                if command.cmd == LC_BUILD_VERSION:
                    minimum = version.minos
                elif command.cmd == LC_VERSION_MIN_MACOSX:
                    minimum = version.version
                if minimum is not None and minimum > MAX_MACOS_VERSION:
                    raise ValueError(f"Requires macOS newer than 13: {path.relative_to(app)}")
        checked += 1
    if checked == 0:
        raise ValueError("No Mach-O binaries found")
    print(f"Verified {checked} Mach-O binaries: {architecture}, minimum macOS <= 13.0")


if __name__ == "__main__":
    verify(Path(sys.argv[1]), sys.argv[2])
