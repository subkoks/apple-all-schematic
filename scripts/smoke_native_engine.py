#!/usr/bin/env python3
"""Verify the bundled JSON engine outside the repository working directory, offline."""

import json
import subprocess
import tempfile
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENGINE = REPO / "dist/native/BoardVault.app/Contents/Resources/engine/boardvault-engine"
TIMEOUT_SECONDS = 20


def operation(root, name, extra=()):
    command = [
        str(ENGINE),
        "--json",
        "--operation",
        name,
        "--data-dir",
        str(root),
        "--download-dir",
        str(root / "downloads"),
        "--organized-dir",
        str(root / "organized"),
        *extra,
    ]
    process = subprocess.Popen(
        command,
        cwd=root,
        env={"HOME": str(root), "PATH": "/usr/bin:/bin"},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    timer = threading.Timer(TIMEOUT_SECONDS, process.kill)
    timer.start()
    try:
        events = []
        for line in process.stdout:
            event = json.loads(line)
            events.append(event)
            if event["type"] == "done":
                break
        process.stdin.close()
        returncode = process.wait(timeout=TIMEOUT_SECONDS)
        assert returncode == 0, f"{name}: engine exited {returncode}"
        assert events and events[-1]["type"] == "done" and events[-1]["status"] == "ok"
        assert all(event["type"] != "error" for event in events)
        return events
    finally:
        timer.cancel()
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
        process.stderr.close()


def main():
    root = Path(tempfile.mkdtemp(prefix="native-engine-smoke-", dir=REPO / "build"))
    source = root / "downloads/fixturechannel/iphone.pdf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"fixture-document")
    state = root / "state.json"
    state.write_text(json.dumps({"downloaded": {"fixture:1": str(source)}}))
    assert operation(root, "config")[0]["channels"]
    plan = next(event for event in operation(root, "scan") if event["type"] == "plan")
    destination = Path(plan["moves"][0]["dest"])
    operation(root, "organize", ["--plan-id", plan["planID"]])
    assert destination.read_bytes() == b"fixture-document" and not source.exists()
    operation(root, "undo")
    assert source.read_bytes() == b"fixture-document" and not destination.exists()
    assert json.loads(state.read_text())["downloaded"]["fixture:1"] == str(source)
    report = {"config": True, "scan": True, "organize": True, "undo": True, "restored_state": True}
    (root / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, sort_keys=True))
    print(f"Evidence: {root}")


if __name__ == "__main__":
    main()
