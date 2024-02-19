#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "Smoketest GUI on xwayland"
xwayland-run -decorate -geometry 800x600 -- "${DIR}/../python/legion_linux/legion_linux/legion_gui.py" --use_legion_cli_to_write --automaticclose

echo "Smoketest GUI on wayland"
wlheadless-run -c weston --renderer gl -- "${DIR}/../python/legion_linux/legion_linux/legion_gui.py" --use_legion_cli_to_write --automaticclose
echo "Done"
