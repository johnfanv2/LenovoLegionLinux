#!/bin/bash
set -ex
# Smoketest GUI
#xvfb-run "legion_gui" --automaticclose
xwayland-run :12 -- legion_gui --use_legion_cli_to_write --automaticclose
echo "Done"
