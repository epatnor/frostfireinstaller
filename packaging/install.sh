#!/usr/bin/env bash
# frostfireinstaller installer (curl | bash friendly).
#
#   curl -fsSL https://raw.githubusercontent.com/epatnor/frostfireinstaller/main/packaging/install.sh | bash
#
# Installs the CLI and GUI into an isolated pipx environment. The GUI needs
# PyGObject + GTK4 + libadwaita; those are distro packages for the system Python,
# so pipx is told to expose the system site packages (no compiling). Only when the
# system has no `gi` at all does the installer pull PyGObject into the app
# environment via the `[gui]` extra.

set -euo pipefail

REPO="${FROSTFIREINSTALLER_REPO:-https://github.com/epatnor/frostfireinstaller}"
PIPX_BIN=""

info() { printf '\033[34m[frostfireinstaller]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[frostfireinstaller]\033[0m %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "python3 is missing"
python3 - <<'PY' || fail "Python 3.11+ is required"
import sys
sys.exit(0 if sys.version_info >= (3, 11) else 1)
PY

if command -v pipx >/dev/null 2>&1; then
  PIPX_BIN="$(command -v pipx)"
else
  info "pipx is missing - installing with pip --user"
  python3 -m pip install --user --upgrade pipx
  PIPX_BIN="$(python3 -m site --user-base)/bin/pipx"
fi

# The GUI imports PyGObject (gi) + GTK4 + libadwaita. Prefer the distro's system
# packages (exposed through pipx --system-site-packages); fall back to the pip
# `[gui]` extra only when the system Python cannot import `gi`.
PIPX_FLAGS=(--force)
if python3 -c 'import gi' >/dev/null 2>&1; then
  PIPX_FLAGS+=(--system-site-packages)
  info "Using the system PyGObject (GTK4 + libadwaita)"
  GIT_SPEC="$REPO"
  LOCAL_SPEC="."
else
  info "System PyGObject (gi) not found - installing GTK bindings into the app env"
  info "  Needs a compiler + libgirepository/cairo dev headers. If this fails, install"
  info "  your distro's python3-gobject + gtk4 + libadwaita and re-run this installer."
  GIT_SPEC="frostfireinstaller[gui] @ git+$REPO"
  LOCAL_SPEC=".[gui]"
fi

info "Installing frostfireinstaller ..."
if ! "$PIPX_BIN" install "${PIPX_FLAGS[@]}" "$GIT_SPEC"; then
  info "Falling back to the local source (if you run from a clone)"
  "$PIPX_BIN" install "${PIPX_FLAGS[@]}" "$LOCAL_SPEC"
fi

# Report clearly if the GUI toolkit is not importable from the app venv.
VENV="${PIPX_HOME:-$HOME/.local/share/pipx}/venvs/frostfireinstaller"
if [ -x "$VENV/bin/python" ] && \
   ! "$VENV/bin/python" -c 'import gi, gi.repository.Gtk, gi.repository.Adw' >/dev/null 2>&1; then
  info "WARNING: the GUI toolkit (GTK4/libadwaita) is not importable."
  info "  The CLI still works. For the GUI, install the system packages and re-run:"
  info "    Fedora/Bazzite: preinstalled (python3-gobject)"
  info "    Debian/Ubuntu:  python3-gi gir1.2-gtk-4.0 gir1.2-adw-1"
  info "    Arch:           python-gobject gtk4 libadwaita"
fi

info "Done. Verify with: frostfireinstaller doctor"
info "Start the GUI: frostfireinstaller gui"
