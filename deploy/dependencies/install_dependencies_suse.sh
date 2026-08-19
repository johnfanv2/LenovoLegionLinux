#!/bin/bash
set -ex
# refresh, otherwise sometimes we get "digest failure" because mirror/version changed from last time
sudo zypper refresh
set +e
sudo zypper --non-interactive install make gcc gcc-c++ cmake ninja rpm-build kernel-devel kernel-default-devel git libopenssl-devel sensors dmidecode nlohmann_json-devel yaml-cpp-devel systemd-rpm-macros python3-devel 'python3dist(build)' 'python3dist(installer)' 'python3dist(setuptools)' 'python3dist(wheel)' 'python3dist(PyQt6)' 'python3dist(PyYAML)' 'python3dist(Pillow)'
ecode=$?
if [ "$ecode" != 0 -a "$ecode" != 107 -a "$ecode" != 130 ]; then
	exit 1
fi
set -e
# allow post-script install to fail (107) because it will try to update initramfs which is not possible inside container
sudo zypper --non-interactive install 'python3dist(argcomplete)' 'python3dist(darkdetect)'
sudo zypper --non-interactive install dkms openssl mokutil
