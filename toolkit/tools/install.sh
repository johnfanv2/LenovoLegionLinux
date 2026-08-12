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

echo ">> Installed. Verify with:  python3 $DEST/legion-cli.py --help"
