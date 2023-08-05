#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd ${DIR}/../python/legion_linux
#mkdir $HOME/.config/lenovo_linux

# Build and install python package with build and installer
python3 -m build --wheel --no-isolation

if [ "$EUID" -ne 0 ]
  then echo "Please run as root to install"
  exit
else
    python3 -m installer --destdir="/" dist/*.whl
    #Create config folder
    cp -r /usr/share/legion_linux /etc/legion_linux
fi
# sudo cp legion_linux/legion_gui.desktop /usr/share/applications/
# sudo cp legion_linux/legion_gui_user.desktop /usr/share/applications/
# sudo cp legion_linux/legion_cli.policy /usr/share/polkit-1/actions/

echo "Done"