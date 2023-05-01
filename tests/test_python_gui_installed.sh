#!/bin/bash
set -ex
# Smoketest GUI
xvfb-run "legion_gui" --automaticclose
echo "Done"