#!/bin/bash
cd python/kernel_module
python3 -m pip install --upgrade build
python3 -m build
sudo python3 -m pip install -e .

# Desktop file
sudo desktop-file-install legion_gui.desktop
sudo mkdir -p /usr/share/icons/
sudo cp legion_logo.png /usr/share/icons/legion_logo.png

