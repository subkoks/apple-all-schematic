# Native release documentation follow-up — 2026-10-06

The native implementation merged in PR #40. This follow-up makes the README show the actual
native interface, fixes release-page documentation links, and records the successful GitHub
checks and uploaded asset verification. It does not change the shipped app or Python engine.

## Focused review

Reviewed the JSON command/event boundary, sidecar crash/cancellation handling, native search,
download publication and resume behavior, organizer journal/undo, Swift progress state,
credential handling, library preview entry points, packaging, and corresponding regression tests.
This is a local code review, not an independent security audit or real-account acceptance.

- **Minor, fixed:** release notes used repository-relative guide/source links, which do not
  resolve correctly when copied into GitHub's release description. They now use absolute links.
- **Minor, fixed:** verification and changelog text still described GitHub CI as pending and
  omitted the merged PR. Current status is separated from retained historical build evidence.
- **No Critical/Major finding in the reviewed paths.** Real Keychain, fresh login, interactive
  Quick Look, delivered notifications, accessibility, and actual Ventura execution remain
  unverified. Neither tests nor this review establish those results.

## Validation

- Local: 160 Python tests plus 56 subtests; 15 Intel Swift tests; Ruff, shellcheck, actionlint.
- GitHub: Native checks run 37395186951 and sanity run 37395187085 passed for the final PR head.
- Draft release 404188029: both uploaded archive digests and sizes match the local manifest.
- Desktop fixture evidence: native-smoke-fbr9bylb, including compact rows, light/dark captures,
  scan, organize, undo, clean exit, restored bytes and state.

The publication helper waits for the follow-up's CI, merges through normal protection, updates
the existing release's notes, and publishes it as a prerelease. It preserves binary assets,
source provenance, and the Qt stable release. Untested platform checks remain in release notes.

**Verdict:** documentation follow-up is ready for CI; native 2.1.0-rc.1 is suitable for a
prerelease with the stated limits, not a fully accepted stable release.
