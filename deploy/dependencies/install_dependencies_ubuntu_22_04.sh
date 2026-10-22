#!/bin/bash
set -ex
sudo apt-get update
sudo apt-get install -y make gcc clang build-essential git lm-sensors wget python3-yaml python3-venv python3-pip python3-wheel python3-argcomplete python3-pillow policykit-1
# See install_dependencies_ubuntu_24_04.sh: containers set KERNEL_HEADERS_PACKAGE
# instead of installing headers for the host kernel they happen to share.
if [ -n "${KERNEL_HEADERS_PACKAGE:-}" ]; then
	sudo apt-get install -y "$KERNEL_HEADERS_PACKAGE"
else
	sudo apt-get install -y "linux-headers-$(uname -r)"
fi
sudo apt-get install -y dkms openssl mokutil
sudo pip install PyQt6
