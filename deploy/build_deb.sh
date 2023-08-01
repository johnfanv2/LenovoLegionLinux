#!/bin/bash
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
REPODIR="${DIR}/.."
DKMSDIR=/usr/src/lenovolegionlinux-1.0.0
BUILD_DIR=/tmp/dkms_deb

set -ex
#Intsall debian packages
sudo apt-get install debhelper dkms python3-all python3-stdeb dh-python

# recreate BUILD_DIR for both deb
rm -rf "${BUILD_DIR}" || true
mkdir -p "${BUILD_DIR}"

## BUILD DKMS DEB
#Setup BUILD_DIR
cp --recursive ${REPODIR}/kernel_module/* ${BUILD_DIR}/

cd ${BUILD_DIR}

sudo mkdir --verbose ${DKMSDIR}
sudo cp --recursive * ${DKMSDIR}

#Build dkms
sudo dkms add -m lenovolegionlinux -v 1.0.0
sudo dkms build -m lenovolegionlinux -v 1.0.0

#Build deb file
sudo dkms mkdsc -m lenovolegionlinux -v 1.0.0
sudo dkms mkdeb -m lenovolegionlinux -v 1.0.0

#Copy deb to deploy folder
sudo ls /var/lib/dkms/lenovolegionlinux/1.0.0/deb/
cp /var/lib/dkms/lenovolegionlinux/1.0.0/deb/lenovolegionlinux-dkms_1.0.0_amd64.deb ${BUILD_DIR}/lenovolegionlinux-dkms_1.0.0_amd64.deb
echo "Dkms deb located at ${BUILD_DIR}/lenovolegionlinux-dkms_1.0.0_amd64.deb"
##

##BUILD PYTHON DEB
cd ${REPODIR}/python/legion_linux

#Build deb
sudo python3 setup.py --command-packages=stdeb.command sdist_dsc
cd deb_dist/legion-linux-1.0.0
sudo dpkg-buildpackage -uc -us
cp ../python3-legion-linux_1.0.0-1_all.deb ${BUILD_DIR}/python3-legion-linux_1.0.0-1_amd64.deb