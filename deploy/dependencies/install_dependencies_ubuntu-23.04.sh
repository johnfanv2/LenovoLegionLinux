#!/bin/bash
set -ex
sudo apt-get update
sudo apt-get install -y make gcc linux-headers-generic build-essential git lm-sensors wget python3-yaml python3-venv python3-pip python3-wheel python3-argcomplete policykit-1
sudo apt-get install -y dkms openssl mokutil

cd /tmp/
wget http://archive.ubuntu.com/ubuntu/pool/main/l/linux-azure-6.2/linux-azure-6.2-headers-6.2.0-1019_6.2.0-1019.19~22.04.1_all.deb

wget http://archive.ubuntu.com/ubuntu/pool/main/l/linux-azure-6.2/linux-headers-6.2.0-1019-azure_6.2.0-1019.19~22.04.1_amd64.deb

sudo apt install -f ./linux-azure-6.2-headers-6.2.0-1019_6.2.0-1019.19~22.04.1_all.deb

sudo apt install -f ./linux-headers-6.2.0-1019-azure_6.2.0-1019.19~22.04.1_amd64.deb

sudo pip install --break-system-packages PyQt6
