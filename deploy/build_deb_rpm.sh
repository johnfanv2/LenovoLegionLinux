#!/bin/bash
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
REPODIR="${DIR}/.."
DKMSDIR=/usr/src/lenovolegionlinux-1.0.0
BUILD_DIR=/tmp/pkg

set -ex
#Intsall debian packages
#sudo apt-get install debhelper dkms python3-all python3-stdeb dh-python alien rpm

# recreate BUILD_DIR for both deb
rm -rf "${BUILD_DIR}" || true
mkdir -p "${BUILD_DIR}"

## BUILD DKMS DEB
#Setup BUILD_DIR
cp --recursive ${REPODIR}/kernel_module/* ${BUILD_DIR}/

cd ${BUILD_DIR}

# recreate DKMSDIR and copy files
sudo rm -rf "${DKMSDIR}" || true
sudo mkdir --verbose ${DKMSDIR}
sudo cp --recursive * ${DKMSDIR}

#Build dkms
sudo dkms add -m lenovolegionlinux -v 1.0.0
sudo dkms build -m lenovolegionlinux -v 1.0.0

#Build deb file
sudo dkms mkdsc -m lenovolegionlinux -v 1.0.0
sudo dkms mkdeb -m lenovolegionlinux -v 1.0.0

#Copy deb to deploy folder
cp /var/lib/dkms/lenovolegionlinux/1.0.0/deb/lenovolegionlinux-dkms_1.0.0_amd64.deb ${BUILD_DIR}/lenovolegionlinux-dkms_1.0.0_amd64.deb
echo "Dkms deb located at ${BUILD_DIR}/lenovolegionlinux-dkms_1.0.0_amd64.deb"
##

#BUILD DKMS RPM

#Clean DKSM tree
sudo dkms remove -m lenovolegionlinux -v 1.0.0

#Build rpm file
sudo dkms mkkmp -m lenovolegionlinux -v 1.0.0 --spec lenovolegionlinux.spec

#Copy rpm to deploy folder
cp /var/lib/dkms/lenovolegionlinux/1.0.0/rpm/lenovolegionlinux-1.0-0.src.rpm ${BUILD_DIR}/lenovolegionlinux-1.0-0.src.rpm
##

##BUILD PYTHON DEB
cd ${REPODIR}/python/legion_linux

# Create package sceleton
sudo python3 setup.py --command-packages=stdeb.command sdist_dsc
cd deb_dist/legion-linux-1.0.0

##Add to debial install
sudo cp -R ../../../../extra/service/legion-linux.service .
sudo cp -R ../../../../extra/service/legion-linux.path .
echo "legion-linux.service /etc/systemd/system/" | sudo tee -a debian/install
echo "legion-linux.path /lib/systemd/system/" | sudo tee -a debian/install
sudo  EDITOR=/bin/true dpkg-source -q --commit . p1

# Build package
sudo dpkg-buildpackage -uc -us
cp ../python3-legion-linux_1.0.0-1_all.deb ${BUILD_DIR}/python3-legion-linux_1.0.0-1_amd64.deb

#Build to RPM
cd ${BUILD_DIR}
mkdir -p rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
cp ${REPODIR}/deploy/lenovolegionlinux.spec rpmbuild/SPECS
cp -r ${REPODIR}/python/legion_linux lenovolegionlinux-1.0.0
tar --create --file lenovolegionlinux-1.0.0.tar.gz lenovolegionlinux-1.0.0
mv lenovolegionlinux-1.0.0.tar.gz rpmbuild/SOURCES
cd rpmbuild
rpmbuild --define "_topdir `pwd`" -bs SPECS/lenovolegionlinux-1.0.0
mv SRPMS/python-lenovolegionlinux-1.0.0-1.src.rpm ${BUILD_DIR}/