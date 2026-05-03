# Security Policy

## Reporting a vulnerability

This project scrapes public Telegram channels for hardware reference material.
If you find a security issue (RCE in scripts, SSRF, leaked secrets in artifacts,
supply-chain risk in pinned dependencies, etc.), **do not** open a public
issue. Use GitHub's private vulnerability reporting:

- <https://github.com/subkoks/apple-all-schematic/security/advisories/new>

If private reporting is unavailable, contact the maintainer through the
Twitter/X handle linked from <https://github.com/subkoks>.

Please include:

- A description of the issue and the impact.
- Steps to reproduce, ideally with a minimal proof of concept.
- Affected version or commit SHA.
- Your environment (OS, Python version).

## Out of scope

- Issues that depend on the user supplying malicious Telegram credentials or
  altering local config to execute code on their own machine.
- Rate-limiting / TOS concerns of upstream Telegram channels (please report
  those upstream).

## Disclosure

We aim to acknowledge a report within 7 days and to ship a fix or mitigation
before public disclosure when feasible. Reporters are credited in release
notes unless they request otherwise.

## Supported versions

Only the latest commit on `main` is actively supported.
