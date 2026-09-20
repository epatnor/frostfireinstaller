#!/usr/bin/env bash
# frostfireinstaller installer (curl | bash friendly).
#
#   curl -fsSL https://raw.githubusercontent.com/OWNER/frostfireinstaller/main/packaging/install.sh | bash
#
# Installs the CLI (and GUI) into an isolated pipx environment.

set -euo pipefail

REPO="${FROSTFIREINSTALLER_REPO:-https://github.com/OWNER/frostfireinstaller}"
PIPX_BIN=""

info() { printf '\033[34m[frostfireinstaller]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[frostfireinstaller]\033[0m %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "python3 saknas"
python3 - <<'PY' || fail "Python 3.11+ krävs"
import sys
sys.exit(0 if sys.version_info >= (3, 11) else 1)
PY

if command -v pipx >/dev/null 2>&1; then
  PIPX_BIN="$(command -v pipx)"
else
  info "pipx saknas – installerar med pip --user"
  python3 -m pip install --user --upgrade pipx
  PIPX_BIN="$(python3 -m site --user-base)/bin/pipx"
fi

info "Installerar frostfireinstaller ..."
if ! "$PIPX_BIN" install --force "$REPO"; then
  info "Föll tillbaka på lokal källa (om du kör från ett klonat repo)"
  "$PIPX_BIN" install --force .
fi

info "Klart. Verifiera med: frostfireinstaller doctor"
info "Starta GUI: frostfireinstaller gui"
