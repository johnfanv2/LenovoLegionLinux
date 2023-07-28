#!/bin/bash
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
REPODIR="${DIR}/.."
DKMSDIR=/usr/src/LenovoLegionLinux-1.0.0
BUILD_DIR=/tmp/dkms_deb

set -ex
#Intsall debian packages
sudo apt-get install debhelper dkms linux-headers-$(uname -r)

# recreate BUILD_DIR
rm -rf "${BUILD_DIR}" || true
mkdir -p "${BUILD_DIR}"

#Setup BUILD_DIR
cp --recursive ${REPODIR}/kernel_module/* ${BUILD_DIR}/

cd ${BUILD_DIR}

sudo mkdir --verbose ${DKMSDIR}
sudo cp --recursive * ${DKMSDIR}

#Build dkms
sudo dkms add -m LenovoLegionLinux -v 1.0.0
sudo dkms build -m LenovoLegionLinux -v 1.0.0

#Build deb file
sudo dkms mkdsc -m LenovoLegionLinux -v 1.0.0
sudo dkms mkdeb -m LenovoLegionLinux -v 1.0.0

#Copy deb to deploy folder
cp /var/lib/dkms/LenovoLegionLinux/1.0.0/deb/LenovoLegionLinux-dkms_1.0.0_all.deb ${BUILD_DIR}/LenovoLegionLinux-dkms_1.0.0_all.deb
echo "Dkms deb located at ${BUILD_DIR}/LenovoLegionLinux-dkms_1.0.0_all.deb"