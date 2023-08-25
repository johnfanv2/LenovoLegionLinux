#!/bin/bash
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
REPODIR="${DIR}/.."
DKMSDIR=/usr/src/lenovolegionlinux-1.0.0
BUILD_DIR=/tmp/rpm

set -ex
#Intsall debian packages
sudo apt-get install dkms python3-all dh-python

# recreate BUILD_DIR for both deb
rm -rf "${BUILD_DIR}" || true
mkdir -p "${BUILD_DIR}"

## BUILD DKMS rpm
#Setup BUILD_DIR
cp --recursive ${REPODIR}/kernel_module/* ${BUILD_DIR}/

cd ${BUILD_DIR}

sudo mkdir --verbose ${DKMSDIR}
sudo cp --recursive * ${DKMSDIR}

#Build dkms
sudo dkms add -m lenovolegionlinux -v 1.0.0
sudo dkms build -m lenovolegionlinux -v 1.0.0

#Build rpm file
sudo dkms mkrpm -m lenovolegionlinux -v 1.0.0 --source-only
sudo dkms mkrpm -m lenovolegionlinux -v 1.0.0 --source-only

#Copy rpm to deploy folder
sudo ls /var/lib/dkms/lenovolegionlinux/1.0.0/rpm/
cp /var/lib/dkms/lenovolegionlinux/1.0.0/rpm/lenovolegionlinux-dkms_1.0.0_amd64.rpm ${BUILD_DIR}/lenovolegionlinux-dkms_1.0.0_amd64.rpm
echo "Dkms deb located at ${BUILD_DIR}/lenovolegionlinux-dkms_1.0.0_amd64.deb"
##

##BUILD PYTHON DEB
#cd ${REPODIR}/python/legion_linux

# Create package sceleton
#sudo python3 setup.py --command-packages=stdeb.command sdist_dsc
#cd deb_dist/legion-linux-1.0.0

##Add to debial install
#sudo cp -R ../../../../extra/service/legion-linux.service .
#sudo cp -R ../../../../extra/service/legion-linux.path .
#echo "legion-linux.service /etc/systemd/system/" | sudo tee -a debian/install
#echo "legion-linux.path /lib/systemd/system/" | sudo tee -a debian/install
#sudo  EDITOR=/bin/true dpkg-source -q --commit . p1

# Build package
#sudo dpkg-buildpackage -uc -us
#cp ../python3-legion-linux_1.0.0-1_all.deb ${BUILD_DIR}/python3-legion-linux_1.0.0-1_amd64.deb