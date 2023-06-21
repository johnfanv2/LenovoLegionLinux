#!/bin/bash
read -p "This script Install systemd service" -n 1 -r

sudo cp service/fancurve-set /usr/bin/

mkdir /usr/share/legion_linux/

cp service/.env $HOME/.config/lenovo_linux/
cp service/.env /usr/share/legion_linux/

cp -r service/profiles/* $HOME/.config/lenovo_linux
cp -r service/profiles/* cp service/.env /usr/share/legion_linux/

sudo cp service/{legion-linux.service,legion-linux.path} /etc/systemd/system/

#force to disable the service (pls enable in the gui)
systemctl disable --now legion-linux.service,legion-linux.path

echo "Done"