#!/bin/bash
set -ex
# Smoketest GUI
# See tests/test_python_gui.sh: skip the flaky Xvfb server when Qt does not
# use the xcb platform (e.g. QT_QPA_PLATFORM=offscreen in container CI).
if [ "${QT_QPA_PLATFORM:-xcb}" = "xcb" ]; then
	xvfb-run "legion_gui" --automaticclose
else
	legion_gui --automaticclose
fi
echo "Done"