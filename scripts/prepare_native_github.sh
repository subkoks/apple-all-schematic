#!/usr/bin/env bash
# Push committed source, open a draft PR, verify CI, then create a draft prerelease.
# Never merges, publishes, overwrites release assets, or stages working-tree changes.
# Exit 0: complete/local checks pass; 1: failed gate; 2: invalid arguments.
set -euo pipefail
IFS=$'\n\t'

if [[ "${1:-}" == --help ]]; then
    echo 'Usage: scripts/prepare_native_github.sh [--check]'
    echo 'Run in normal Terminal with working GitHub CLI and Git authentication.'
    exit 0
fi
CHECK_ONLY=false
if [[ "${1:-}" == --check ]]; then CHECK_ONLY=true; shift; fi
if [[ $# -ne 0 ]]; then echo 'Unexpected arguments.' >&2; exit 2; fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"
REPO='subkoks/apple-all-schematic'
BRANCH="$(git branch --show-current)"
if [[ "${BRANCH}" != feat/native-swiftui ]]; then
    echo 'Requires the prepared feat/native-swiftui branch.' >&2
    exit 1
fi
RELEASE_VERSION="$(python3 -c 'import json; print(json.load(open("native/release.json"))["release_version"])')"
PACKAGE="${PROJECT_DIR}/dist/releases/${RELEASE_VERSION}-x86_64"
TAG="native-v${RELEASE_VERSION}"

# Match archive bytes against the manifest; reject production changes since the build.
SOURCE_COMMIT="$(python3 - "${PACKAGE}" <<'PYTHON'
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

package = Path(sys.argv[1])
manifest = json.loads((package / "release.json").read_text())
metadata = json.loads(Path("native/release.json").read_text())
assert manifest["release_version"] == metadata["release_version"]
assert not manifest["modified_build_inputs"], "Rebuild from committed release inputs"
source = manifest["source_commit"]
assert re.fullmatch(r"[0-9a-f]{40}", source), "Invalid source commit"
assert {Path(a["file"]).suffix for a in manifest["assets"]} == {".dmg", ".zip"}
for asset in manifest["assets"]:
    filename = asset["file"]
    assert Path(filename).name == filename and filename.startswith("BoardVault-")
    data = (package / filename).read_bytes()
    assert len(data) == asset["bytes"] and hashlib.sha256(data).hexdigest() == asset["sha256"]
inputs = ["native", "src", "args", "context", "pyproject.toml"]
assert not subprocess.check_output(["git", "diff", "--name-only", source, "HEAD", "--", *inputs]), "Production source changed: rebuild first"
assert not subprocess.check_output(["git", "diff", "HEAD", "--name-only", "--", *inputs]), "Uncommitted production inputs: commit and rebuild first"
print(source)
PYTHON
)"
(cd "${PACKAGE}" && shasum -a 256 -c SHA256SUMS)
if [[ "${CHECK_ONLY}" == true ]]; then
    echo 'Local release gates passed; no GitHub mutation performed.'
    exit 0
fi

gh repo view "${REPO}" --json nameWithOwner --jq .nameWithOwner
git push -u origin "${BRANCH}"
PR_URL="$(gh pr list --repo "${REPO}" --head "${BRANCH}" --state open --json url --jq '.[0].url // empty')"
if [[ -z "${PR_URL}" ]]; then
    BODY="${PROJECT_DIR}/build/native-pr-body.md"
    if [[ ! -f "${BODY}" ]]; then BODY="${PROJECT_DIR}/docs/releases/${RELEASE_VERSION}.md"; fi
    PR_URL="$(gh pr create --repo "${REPO}" --base main --head "${BRANCH}" --draft \
        --title 'feat(native): add polished SwiftUI frontend and Intel release candidate' --body-file "${BODY}")"
fi
echo "PR: ${PR_URL}"

# GitHub needs a short interval to register newly triggered checks.
CHECK_REGISTRATION_ATTEMPTS=30
CHECK_REGISTRATION_INTERVAL=2
for ((attempt=0; attempt<CHECK_REGISTRATION_ATTEMPTS; attempt++)); do
    if gh pr checks "${PR_URL}" --repo "${REPO}" --json name > build/native-github-checks.json 2>/dev/null; then break; fi
    sleep "${CHECK_REGISTRATION_INTERVAL}"
done
gh pr checks "${PR_URL}" --repo "${REPO}" --watch --fail-fast
gh pr checks "${PR_URL}" --repo "${REPO}" --json name,state > build/native-github-checks.json
python3 - <<'PYTHON'
import json
from pathlib import Path
checks = json.loads(Path("build/native-github-checks.json").read_text())
for name in ("Python tests", "Swift tests (Intel)"):
    matching = [check for check in checks if check["name"] == name]
    assert matching and all(check["state"] == "SUCCESS" for check in matching), f"Required native gate not green: {name}"
PYTHON

if gh release view "${TAG}" --repo "${REPO}" >/dev/null 2>&1; then
    echo "Release ${TAG} already exists; no release or assets changed."
    exit 0
fi
gh release create "${TAG}" "${PACKAGE}"/*.zip "${PACKAGE}"/*.dmg \
    "${PACKAGE}/SHA256SUMS" "${PACKAGE}/release.json" "${PACKAGE}/RELEASE_NOTES.md" \
    --repo "${REPO}" --target "${SOURCE_COMMIT}" --draft --prerelease \
    --title "BoardVault ${RELEASE_VERSION} — Native macOS (Intel)" \
    --notes-file "${PACKAGE}/RELEASE_NOTES.md"
echo 'Draft prerelease prepared. Nothing merged or published; manual platform gates remain.'
