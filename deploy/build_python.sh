#!/bin/bash
set -ex
cd python/legion_linux
python3 -m pip install --upgrade build
python3 -m build
sudo python3 -m pip install -e .

# Desktop file
sudo cp legion_gui.desktop /usr/share/applications/
sudo mkdir -p /usr/share/icons/
sudo cp legion_logo.png /usr/share/icons/legion_logo.png

