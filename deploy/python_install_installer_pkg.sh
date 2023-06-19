#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd ${DIR}/../python/legion_linux
#mkdir $HOME/.config/lenovo_linux

# Build and install python package with build and installer
python3 -m build --wheel --no-isolation
python3 -m installer --destdir="/" dist/*.whl

sudo cp legion_linux/legion_gui.desktop /usr/share/applications/
sudo cp legion_linux/legion_cli.policy /usr/share/polkit-1/actions/

echo "Done"