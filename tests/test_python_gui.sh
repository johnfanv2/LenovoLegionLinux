#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Smoketest GUI
#xvfb-run "${DIR}/../python/legion_linux/legion_linux/legion_gui.py" --automaticclose
xwayland-run :12 -- legion_gui --use_legion_cli_to_write --automaticclose
