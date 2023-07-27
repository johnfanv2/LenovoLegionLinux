#!/bin/bash
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
REPODIR="${DIR}/.."
DKMSDIR=/usr/src/LenovoLegionLinux-1.0.0
BUILD_DIR=/tmp/linux

set -ex
sudo apt-get install debhelper dkms linux-headers-$(uname -r)

cp -r ${REPODIR}/kernel_module/ ${BUILD_DIR}/

cd ${BUILD_DIR}

sudo mkdir --verbose ${DKMSDIR}
sudo cp --recursive * ${DKMSDIR}

#Build dkms
sudo dkms add -m LenovoLegionLinux -v 1.0.0
sudo dkms build -m LenovoLegionLinux -v 1.0.0

#Make deb file
sudo dkms mkdsc -m LenovoLegionLinux -v 1.0.0
sudo dkms mkdeb -m LenovoLegionLinux -v 1.0.0

#copy deb to kernel_module folder
cp /var/lib/dkms/LenovoLegionLinux/1.0.0/deb/LenovoLegionLinux-dkms_1.0.0_all.deb ./LenovoLegionLinux-dkms_1.0.0_all.deb