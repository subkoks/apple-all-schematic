#!/usr/bin/env bash
# Merge the documentation follow-up after CI and publish the existing native prerelease.
# Never creates a stable release, bypasses protection, or replaces binary assets.
# Exit 0: complete/local gates pass; 1: failed gate; 2: invalid arguments.
set -euo pipefail
IFS=$'\n\t'

if [[ "${1:-}" == --help ]]; then
    echo 'Usage: scripts/finalize_native_release.sh [--check]'
    echo 'Normal Terminal: push docs, await CI, merge, update notes, publish existing prerelease.'
    exit 0
fi
CHECK_ONLY=false
if [[ "${1:-}" == --check ]]; then CHECK_ONLY=true; shift; fi
if [[ $# -ne 0 ]]; then echo 'Unexpected arguments.' >&2; exit 2; fi
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"
REPO='subkoks/apple-all-schematic'
BRANCH='docs/native-release-polish'
TAG='native-v2.1.0-rc.1'
PACKAGE='dist/releases/2.1.0-rc.1-x86_64'
NOTES='docs/releases/2.1.0-rc.1.md'
if [[ "$(git branch --show-current)" != "${BRANCH}" ]]; then
    echo "Requires prepared branch ${BRANCH}." >&2; exit 1
fi
if [[ -n "$(git status --porcelain -- README.md CHANGELOG.md docs scripts/finalize_native_release.sh)" ]]; then
    echo 'Commit the prepared documentation before publishing.' >&2; exit 1
fi
(cd "${PACKAGE}" && shasum -a 256 -c SHA256SUMS)
if [[ "${CHECK_ONLY}" == true ]]; then
    echo 'Local release gates passed; no GitHub changes made.'
    exit 0
fi

# Verify uploaded archives and the original source commit before any remote mutation.
mkdir -p build
gh api "repos/${REPO}/releases" > build/native-publication-releases.json
python3 - "${PACKAGE}" "${TAG}" <<'PYTHON'
import json
import subprocess
import sys
from pathlib import Path

manifest = json.loads((Path(sys.argv[1]) / "release.json").read_text())
releases = json.loads(Path("build/native-publication-releases.json").read_text())
matching = [release for release in releases if release["tag_name"] == sys.argv[2]]
assert len(matching) == 1, "Expected exactly one native candidate release"
release = matching[0]
assert release["prerelease"], "Refusing to change a stable release"
assert release["target_commitish"] == manifest["source_commit"]
assert not manifest["modified_build_inputs"]
assert {Path(asset["file"]).suffix for asset in manifest["assets"]} == {".zip", ".dmg"}
for asset in manifest["assets"]:
    uploaded = [item for item in release["assets"] if item["name"] == asset["file"]]
    assert len(uploaded) == 1
    assert uploaded[0]["state"] == "uploaded" and uploaded[0]["size"] == asset["bytes"]
    assert uploaded[0]["digest"] == "sha256:" + asset["sha256"], "Uploaded archive mismatch"
inputs = ["native", "src", "args", "context", "pyproject.toml", "LICENSE"]
assert not subprocess.check_output(["git", "diff", "--name-only", manifest["source_commit"], "HEAD", "--", *inputs]), "Runtime changed: rebuild and prepare a new candidate"
PYTHON

git push -u origin "${BRANCH}"
PR_URL="$(gh pr list --repo "${REPO}" --head "${BRANCH}" --state all --json url --jq '.[0].url // empty')"
if [[ -z "${PR_URL}" ]]; then
    PR_URL="$(gh pr create --repo "${REPO}" --base main --head "${BRANCH}" --draft \
        --title 'docs(native): polish release presentation and record verified GitHub checks' \
        --body-file docs/native-release-review.md)"
fi
if [[ "$(gh pr view "${PR_URL}" --repo "${REPO}" --json state --jq .state)" != MERGED ]]; then
    CHECK_REGISTRATION_ATTEMPTS=30
    CHECK_REGISTRATION_INTERVAL=2
    for ((attempt=0; attempt<CHECK_REGISTRATION_ATTEMPTS; attempt++)); do
        if gh pr checks "${PR_URL}" --repo "${REPO}" --json name > build/native-publication-checks.json 2>/dev/null; then break; fi
        sleep "${CHECK_REGISTRATION_INTERVAL}"
    done
    gh pr checks "${PR_URL}" --repo "${REPO}" --watch --fail-fast
    gh pr checks "${PR_URL}" --repo "${REPO}" --json name,state > build/native-publication-checks.json
    python3 - <<'PYTHON'
import json
from pathlib import Path
checks = json.loads(Path("build/native-publication-checks.json").read_text())
for name in ("Python tests", "Swift tests (Intel)", "sanity"):
    matching = [check for check in checks if check["name"] == name]
    assert matching and all(check["state"] == "SUCCESS" for check in matching), name
PYTHON
    EXPECTED_HEAD="$(gh pr view "${PR_URL}" --repo "${REPO}" --json headRefOid --jq .headRefOid)"
    if [[ "${EXPECTED_HEAD}" != "$(git rev-parse HEAD)" ]]; then echo 'PR head changed; review it first.' >&2; exit 1; fi
    gh pr ready "${PR_URL}" --repo "${REPO}"
    if [[ "$(gh pr view "${PR_URL}" --repo "${REPO}" --json state --jq .state)" != MERGED ]]; then
        gh pr merge "${PR_URL}" --repo "${REPO}" --squash --match-head-commit "${EXPECTED_HEAD}"
    fi
fi
if [[ "$(gh pr view "${PR_URL}" --repo "${REPO}" --json state --jq .state)" != MERGED ]]; then
    echo 'Documentation merge pending; release left unchanged.' >&2; exit 1
fi

# Retain previous notes before replacing only the notes attachment and release body.
STAGE="$(mktemp -d "${PROJECT_DIR}/build/native-publication.XXXXXX")"
gh release download "${TAG}" --repo "${REPO}" --pattern RELEASE_NOTES.md --dir "${STAGE}/previous"
cp "${NOTES}" "${STAGE}/RELEASE_NOTES.md"
gh release upload "${TAG}" "${STAGE}/RELEASE_NOTES.md" --repo "${REPO}" --clobber
gh release edit "${TAG}" --repo "${REPO}" --notes-file "${NOTES}" --draft=false --prerelease --latest=false
gh release view "${TAG}" --repo "${REPO}" --json url,isDraft,isPrerelease > build/native-publication-result.json
python3 - <<'PYTHON'
import json
from pathlib import Path
release = json.loads(Path("build/native-publication-result.json").read_text())
assert not release["isDraft"] and release["isPrerelease"]
print(release["url"])
PYTHON
