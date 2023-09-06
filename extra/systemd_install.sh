#!/bin/bash

#Force run with root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

read -p "This script will Install the systemd service files" -n 1 -r

sudo cp service/{legion-linux.service,legion-linux.path} /etc/systemd/system/

#Force to disable the service (Please enable in the gui)
systemctl daemon-reload
systemctl disable --now legion-linux.service,legion-linux.path

echo "Done"