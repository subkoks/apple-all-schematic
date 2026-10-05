#!/usr/bin/env python3
"""Launch the built app on disposable fixtures, capture its window, verify organize/undo.

Requires a logged-in macOS desktop. No credentials, Keychain or real sessions are used.
"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "dist/native/BoardVault.app/Contents/MacOS/BoardVault"
SMOKE_TIMEOUT_SECONDS = 60


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=APP.parents[2])
    app = parser.parse_args().app.resolve() / "Contents/MacOS/BoardVault"
    root = Path(tempfile.mkdtemp(prefix="native-smoke-", dir=REPO / "build"))
    source = root / "downloads/fixturechannel/iphone.pdf"
    source.parent.mkdir(parents=True)
    original = b"%PDF-1.4\n% BoardVault fixture only\n%%EOF\n"
    source.write_bytes(original)
    (root / "state.json").write_text(json.dumps({"downloaded": {"fixturechannel:1": str(source)}}))
    (REPO / "build/last-native-smoke.txt").write_text(str(root))
    with (root / "app.log").open("w") as log:
        result = subprocess.run(
            [str(app), "--ui-smoke"],
            env={
                "HOME": str(Path.home()),
                "PATH": "/usr/bin:/bin",
                "BOARDVAULT_FIXTURE_ROOT": str(root),
            },
            stdout=log,
            stderr=log,
            timeout=SMOKE_TIMEOUT_SECONDS,
            check=False,
        )
    report = root / "ui-smoke.json"
    checks = json.loads(report.read_text()) if report.exists() else {"report": False}
    checks["clean_exit"] = result.returncode == 0
    checks["restored_bytes"] = source.exists() and source.read_bytes() == original
    checks["restored_state"] = json.loads((root / "state.json").read_text()) == {
        "downloaded": {"fixturechannel:1": str(source)}
    }
    report.write_text(json.dumps(checks, indent=2))
    print(f"App exit code: {result.returncode}")
    print(json.dumps(checks, sort_keys=True))
    print(f"Evidence: {root}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
