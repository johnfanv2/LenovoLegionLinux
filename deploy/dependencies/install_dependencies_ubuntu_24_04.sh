#!/bin/bash
set -ex
sudo apt-get update
sudo apt-get install -y make gcc clang linux-headers-$(uname -r) build-essential git lm-sensors wget python3-pyqt6 python3-yaml python3-venv python3-pip python3-wheel python3-argcomplete policykit-1
sudo apt-get install -y dkms openssl mokutil
