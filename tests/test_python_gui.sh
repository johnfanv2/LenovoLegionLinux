#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Smoketest GUI
xvfb-run "${DIR}/../python/legion_linux/legion_gui.py" --automaticclose --donotexpecthwmon