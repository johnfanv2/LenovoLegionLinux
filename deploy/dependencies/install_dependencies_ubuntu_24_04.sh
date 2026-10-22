#!/bin/bash
set -ex
sudo apt-get update
sudo apt-get install -y make gcc clang build-essential git lm-sensors wget python3-pyqt6 python3-yaml python3-venv python3-pip python3-wheel python3-argcomplete policykit-1
# Containers share the host kernel, so `uname -r` inside an image is whatever
# kernel the host happens to run - on CI runners that differs between runners
# and changes with runner image updates, and the matching header package is not
# always in this distribution's archive. Images therefore set
# KERNEL_HEADERS_PACKAGE to their own headers; tests/kernel_version.sh builds
# the module against those. Everywhere else the running kernel's headers are
# required.
if [ -n "${KERNEL_HEADERS_PACKAGE:-}" ]; then
	sudo apt-get install -y "$KERNEL_HEADERS_PACKAGE"
else
	sudo apt-get install -y "linux-headers-$(uname -r)"
	# The reload test needs wmi/platform_profile. Older kernels ship them in
	# linux-modules-extra; newer ones (e.g. the 7.0 azure kernel) fold them into
	# linux-modules and no longer publish an -extra package.
	if apt-cache show "linux-modules-extra-$(uname -r)" >/dev/null 2>&1; then
		sudo apt-get install -y "linux-modules-extra-$(uname -r)"
	fi
fi
sudo apt-get install -y dkms openssl mokutil python3-pillow
