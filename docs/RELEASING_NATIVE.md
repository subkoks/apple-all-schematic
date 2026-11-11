# Preparing a native GitHub release

Candidate: **2.1.0-rc.1**, intended tag **native-v2.1.0-rc.1**. No tag or release is created by
the build scripts. The native version/build has one source: `native/release.json`. Python/Qt stay at
2.0.0; the native candidate has a separate bundle identifier and release asset names.

## Local gates

Run from the repository on an Intel Mac:

```bash
(cd tests && PYTHONPATH=../src PYTHON_DOTENV_DISABLED=1 ../.venv/bin/python -m pytest -q -c ../pyproject.toml --rootdir=. --confcutdir=. .)
swift test --package-path native/BoardVault --arch x86_64
shellcheck scripts/build_native_app.sh
actionlint .github/workflows/native-check.yml .github/workflows/native-build.yml
./scripts/build_native_app.sh
PYTHON_DOTENV_DISABLED=1 .venv/bin/python scripts/smoke_native_engine.py
PYTHON_DOTENV_DISABLED=1 .venv/bin/python scripts/smoke_native_app.py
```

Tests and smoke helpers use temporary fixtures; they do not perform real-account login or
downloads. GUI capture needs the user's logged-in desktop. `--app-only` builds the app and a
verified ZIP when disk-image services are unavailable. Keep failed gate evidence; never label
an unavailable desktop or DMG check as passed.

The packager verifies the app version, ZIP integrity, and the extracted app signature. It creates
versioned assets, `SHA256SUMS`, `release.json`, and `RELEASE_NOTES.md` under
`dist/releases/2.1.0-rc.1-x86_64/`. A manifest with `modified_build_inputs: true` needs a rebuild
from committed release source before publication. Previous output is retained under `build/`.
Do not upload an unversioned old DMG from `dist/` when only an app/ZIP was rebuilt.

## Manual acceptance

- Confirm the candidate version/build in Settings → About & Help.
- Check Download at the minimum window width: search options, all selected-channel rows,
  channel menus/counts, and the collapsed log. Check both light and dark appearance.
- Confirm Start/Stop, progress, one real channel download, organize/undo, Library, Quick Look,
  and optional notifications. Real credentials/session access requires the user's exact scope.
- Fresh login and an actual macOS 13 run remain distinct checks. A passing deployment-metadata
  check is not a Ventura runtime test. Record any deferred platform checks in release notes.

## GitHub preparation and publication

Current checkpoint: the native implementation merged through PR #40, Python/Intel Swift CI and
sanity checks passed, and draft release 404188029 has verified uploads. This is a prerelease;
the unverified account/platform checks remain in its notes. See
[verification](native-verification.md) and the [focused review](native-release-review.md).

For the prepared `docs/native-release-polish` follow-up, run
`./scripts/finalize_native_release.sh` in normal Terminal. It verifies the existing uploaded
archive digests/source commit, opens a draft documentation PR, waits for all native and sanity
checks, and merges without an administrative bypass. It backs up and updates only the notes
attachment/body, then publishes the existing candidate as a prerelease without marking it Latest.
It does not replace the archives or alter the Qt stable release. `--check` verifies local gates
without GitHub mutations. This command performs the already-authorized publication; it is not
an additional platform acceptance test.

When the Codex runtime cannot use desktop GitHub authentication, run
`./scripts/prepare_native_github.sh` from the repository in normal Terminal. It verifies the
existing ZIP/DMG against their manifest, rejects changed production inputs, pushes committed
source only, opens or reuses a draft PR, and waits for CI. Both native test jobs must pass before
it creates a draft prerelease with the verified assets. It does not merge or publish. `--check`
runs only the local release gates. Existing releases and unrelated working changes are preserved.

`Native checks` adds Python and Intel Swift test jobs on PRs and main. Its
[`macos-15-intel` runner](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
is a standard GitHub-hosted Intel runner. `Native release candidate` is a manually dispatched
build/upload workflow; it does not publish releases or create tags. CI execution remains pending
until these committed workflows reach GitHub.

Review the branch diff, preserve unrelated policy/config work, and push/open a PR only within
the user's authorization. Keep a preparation PR in draft while gates are pending: the existing
auto-merge workflow enables auto-merge for non-draft same-repository PRs. Once the new jobs have
actually run, require their verified check names in branch protection before marking the PR ready.
After required checks, a reviewed prerelease with explicit deferred platform checks can
use `docs/releases/2.1.0-rc.1.md` as its body and the versioned assets as uploads. Use a prerelease
for this candidate. Inspect the uploaded checksums and manifest before making it available.

Stable promotion requires completion of the deferred account/platform acceptance. Updated release
notes may follow the original binary build: `release.json` continues to identify the source that
produced the archives, while the documentation PR records subsequent acceptance and wording.

Developer ID signing/notarization, universal binaries, and final Ventura acceptance are deferred.
Do not claim Apple notarization for these ad-hoc signed builds.
