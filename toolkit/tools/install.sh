#!/usr/bin/env bash
#
# install.sh — deploy the Legion Toolkit to /usr/lib/legion-toolkit/
#
# Run from the source tree root:  sudo tools/install.sh
# Rebuild the generated dispatchers first with:  python3 tools/build_combined.py
#
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEST="/usr/lib/legion-toolkit"

echo ">> Source: $SRC"
echo ">> Dest:   $DEST"

# Regenerate the dispatchers from custom/ + upstream/ before installing.
python3 "$SRC/tools/build_combined.py"

sudo mkdir -p "$DEST/lib" "$DEST/custom" "$DEST/upstream"

# Generated entry points (self-contained: embed custom code + upstream as base64).
sudo install -m 0755 "$SRC/legion-gui.py"  "$DEST/legion-gui.py"
sudo install -m 0755 "$SRC/legion-cli.py"  "$DEST/legion-cli.py"
sudo install -m 0755 "$SRC/legion-tray.py" "$DEST/legion-tray.py"

# Adapter + the two codebases (kept on disk for auditability / editing).
sudo install -m 0644 "$SRC/lib/lll_adapter.py" "$DEST/lib/lll_adapter.py"
sudo cp -r "$SRC/custom/."  "$DEST/custom/"
sudo cp -r "$SRC/upstream/." "$DEST/upstream/"

# Remove stale backups from earlier manual deploys.
sudo rm -f "$DEST/legion-gui.py.bak" "$DEST/legion-gui.py.bak2"

# Desktop entry must not force a specific Qt platform / display.
DESKTOP="/usr/share/applications/legion-linux-toolkit.desktop"
if [ -f "$DESKTOP" ]; then
    sudo sed -i 's|^Exec=env QT_QPA_PLATFORM=wayland python3 /usr/lib/legion-toolkit/legion-gui.py|Exec=python3 /usr/lib/legion-toolkit/legion-gui.py|' "$DESKTOP"
fi

# PATH entry points so users run `legion-ctl` / `legion-gui` directly.
# These supersede any legacy upstream wrapper of the same name: the toolkit
# dispatcher is model-gated, so on 83SC it runs the custom CLI/GUI and on any
# other model it transparently runs the upstream Legion Linux CLI/GUI.
sudo install -m 0755 "$SRC/tools/legion-ctl" "/usr/local/bin/legion-ctl"
sudo install -m 0755 "$SRC/tools/legion-gui" "/usr/local/bin/legion-gui"

# User systemd unit for the tray (needs a display session, so a *user* service,
# not a system service). Install it for the real invoking user, not root.
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"
USER_UNIT_DIR="$REAL_HOME/.config/systemd/user"
sudo -u "$REAL_USER" install -m 0755 -d "$USER_UNIT_DIR"
sudo -u "$REAL_USER" install -m 0644 "$SRC/systemd/legion-tray.service" "$USER_UNIT_DIR/legion-tray.service"
# Enable (and start now if a session is active). `|| true` so a headless/sudo
# environment without a running user service manager doesn't abort the install.
sudo -u "$REAL_USER" --preserve-env=XDG_RUNTIME_DIR \
    systemctl --user enable --now legion-tray.service 2>/dev/null || true

echo ">> Installed. Verify with:  legion-ctl --help"
