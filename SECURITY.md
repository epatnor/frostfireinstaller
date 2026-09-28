# Security Policy

## Reporting a vulnerability

Please report suspected security issues **privately** via GitHub's
[private vulnerability reporting](https://github.com/epatnor/frostfireinstaller/security/advisories/new)
(Security → Report a vulnerability) rather than a public issue. We aim to
acknowledge reports within a few days.

Include, where possible: affected version/commit, a description, reproduction
steps, and the impact you believe it has.

## Scope

`frostfireinstaller` is a local helper that orchestrates the host's
`umu-launcher` + a Proton build against a dedicated Wine prefix. The security
model is documented in `docs/architecture.md`. In short:

- **No secrets** are stored or required at runtime.
- **No shell**: every subprocess call passes an argument list, never a shell
  string.
- The only download is Blizzard's official Battle.net installer over **HTTPS**;
  its size and SHA-256 are recorded in the installation log.
- Wine/Proton come from the host — nothing is bundled or patched.
- Games run with the user's own filesystem rights inside the prefix; this is a
  Wine property, not something this tool loosens.

Issues in Blizzard's client, Wine, Proton, umu-launcher, your GPU driver, or
your distribution are **out of scope** here — please report those upstream.

## Supported versions

The project is pre-1.0; only the latest release and `main` are supported.
