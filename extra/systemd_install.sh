#!/bin/bash

#Force run with root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

read -p "This script Install systemd service" -n 1 -r

cp service/fancurve-set /usr/bin/

mkdir /usr/share/legion_linux/

cp service/.env /etc/lenovo_linux/
cp service/.env /usr/share/legion_linux/

cp -r service/profiles/* /etc/lenovo_linux
cp -r service/profiles/* /usr/share/legion_linux/

sudo cp service/{legion-linux.service,legion-linux.path} /etc/systemd/system/

#force to disable the service (pls enable in the gui)
systemctl disable --now legion-linux.service,legion-linux.path

echo "Done"