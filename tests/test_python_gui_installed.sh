#!/bin/bash
set -ex
# Smoketest GUI

echo "Test GUI on xwayland"
xwayland-run -fullscreen -- legion_gui --use_legion_cli_to_write --automaticclose

echo "Test GUI on wayland"
wlheadless-run -c weston --renderer gl -- legion_gui.py --use_legion_cli_to_write --automaticclose
echo "Done"
