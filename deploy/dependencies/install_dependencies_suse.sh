#!/bin/bash
set -ex
# refresh, otherwise sometimes we get "digest failure" because mirror/version changed from last time
sudo zypper refresh
set +e
sudo zypper --non-interactive install make gcc kernel-devel kernel-default-devel git libopenssl-devel sensors dmidecode python3-qt6 python3-pip python3-wheel python3-PyYAML pkexec
ecode=$?
if [ "$ecode" != 0 -a "$ecode" != 107 -a "$ecode" != 130 ]; then
	exit 1
fi
set -e
# allow post-script install to fail (107) because it will try to update initramfs which is not possible inside container
sudo zypper --non-interactive install python3-argcomplete
sudo zypper --non-interactive install dkms openssl mokutil
