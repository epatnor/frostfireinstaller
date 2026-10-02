# Support and scope

Frostfire Installer is a small open-source helper, provided **as is** without
warranty (see [LICENSE](../LICENSE)). The maintainer offers **best-effort** help
through GitHub issues — no guaranteed fix or response time, and no promise it works
on every system.

**It is** a helper that installs, verifies and repairs Battle.net and launches it
through the host's `umu-launcher` + Proton, in its own Wine prefix, with the known
compatibility fixes. **It is not** a game launcher or library, not a Wine/Proton/
driver (those come from your host), and not affiliated with Blizzard — it does not
modify game files or bundle Blizzard software.

**In scope:** installing/repairing/removing Battle.net and its prefix; the launcher
not starting or showing blank CEF windows; our own packaging, CLI and GUI.

**Out of scope (report upstream):** bugs inside a game (crashes, GPU hangs, freezes),
kernel-level anti-cheat such as Call of Duty's Ricochet, GPU driver bugs (NVIDIA
`Xid`), distribution packaging of Wine/Proton, and Blizzard account/server issues.
Known cases are in [troubleshooting](troubleshooting.md).

**Safety:** the app changes nothing on your system outside its own prefix, config
and desktop entry — system fixes are offered as copy-ready commands; no
telemetry, secrets or accounts; subprocesses take argument lists, never a shell; the
prefix is a normal directory you can inspect, move or delete.

**Reporting:** open an [issue](https://github.com/epatnor/frostfireinstaller/issues/new/choose)
with the `frostfireinstaller doctor` output and, if relevant, the logs from
`~/.local/state/frostfireinstaller/logs`. Security issues: [SECURITY.md](../SECURITY.md).
To the extent permitted by law the authors are not liable for damage or data loss;
the MIT license governs.
