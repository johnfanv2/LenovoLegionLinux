#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd ${DIR}/../python/legion_linux

# Build and install python package with build and installer
python3 -m build --wheel --no-isolation
python3 -m installer --destdir="/" dist/*.whl

sudo cp legion_linux/legion_gui.desktop /usr/share/applications/

echo "Done"