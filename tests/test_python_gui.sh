#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Smoketest GUI
# With a non-X Qt platform (e.g. QT_QPA_PLATFORM=offscreen in container CI) no
# X server is needed, so skip xvfb-run: its Xvfb server is flaky in containers
# (it dies early, which used to abort the GUI mid-startup with SIGABRT or fail
# the script at xvfb-run cleanup with "kill: No such process" and exit code 1).
if [ "${QT_QPA_PLATFORM:-xcb}" = "xcb" ]; then
	xvfb-run "${DIR}/../python/legion_linux/legion_linux/legion_gui.py" --automaticclose
else
	"${DIR}/../python/legion_linux/legion_linux/legion_gui.py" --automaticclose
fi