#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd ${DIR}/../

cd python/legion_linux
python3 -m pip install --upgrade build
python3 -m build
sudo python3 -m pip install -e .

# Desktop file
sudo cp legion_linux/legion_gui.desktop /usr/share/applications/
sudo mkdir -p /usr/share/icons/
sudo cp legion_linux/legion_logo.png /usr/share/icons/legion_logo.png

sudo cp legion_linux/legion_gui.policy /usr/share/polkit-1/actions/