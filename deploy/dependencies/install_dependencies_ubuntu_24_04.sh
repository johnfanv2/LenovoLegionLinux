#!/bin/bash
set -ex
sudo apt-get update
sudo apt-get install -y make gcc clang "linux-headers-$(uname -r)" build-essential git lm-sensors wget python3-pyqt6 python3-yaml python3-venv python3-pip python3-wheel python3-argcomplete policykit-1
# The reload test needs wmi/platform_profile. Older kernels ship them in
# linux-modules-extra; newer ones (e.g. the 7.0 azure kernel) fold them into
# linux-modules and no longer publish an -extra package.
if apt-cache show "linux-modules-extra-$(uname -r)" >/dev/null 2>&1; then
	sudo apt-get install -y "linux-modules-extra-$(uname -r)"
fi
sudo apt-get install -y dkms openssl mokutil python3-pillow
