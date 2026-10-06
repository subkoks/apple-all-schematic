# Native sidecar only. Python's portable build includes its own static TLS support.
import os
from pathlib import Path

repo = Path(SPECPATH).parent
analysis = Analysis(
    [str(repo / "src/tg_schematic_downloader.py")],
    pathex=[str(repo / "src")],
    binaries=[],
    datas=[(str(repo / "context/APPLE_PRODUCT_REFERENCE.md"), "context"),
           (str(repo / "args/config.json"), "args")],
    hiddenimports=["native_engine", "native_organizer"],
    excludes=["PySide6", "qasync", "pytest"],
)
# Telethon's optional ctypes acceleration probes the builder's Homebrew OpenSSL.
# It already falls back to pyaes when versioned libssl is absent. Never ship host
# Homebrew libraries; the verifier rejects remaining external or newer-OS links.
analysis.binaries = [entry for entry in analysis.binaries
                     if not Path(entry[0]).name.startswith(("libssl", "libcrypto"))]
archive = PYZ(analysis.pure)
executable = EXE(archive, analysis.scripts, [], exclude_binaries=True,
                 name="boardvault-engine", console=True,
                 target_arch=os.environ["BOARDVAULT_BUILD_ARCH"])
collection = COLLECT(executable, analysis.binaries, analysis.datas, name="boardvault-engine")
