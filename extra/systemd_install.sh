#!/bin/bash

#Force run with root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

read -p "This script Install systemd service" -n 1 -r

sudo cp service/{legion-linux.service,legion-linux.path} /etc/systemd/system/

#force to disable the service (pls enable in the gui)
systemctl daemon-reload
systemctl disable --now legion-linux.service,legion-linux.path

echo "Done"