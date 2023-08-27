#!/bin/bash
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
REPODIR="${DIR}/.."
DKMSDIR=/usr/src/lenovolegionlinux-1.0.0
BUILD_DIR=/tmp/pkg
BUILD_DIR_RPM_DKMS=/tmp/rpm_dkms

set -ex
#Intsall debian packages
#sudo apt-get install debhelper dkms python3-all python3-stdeb dh-python alien rpm

# recreate BUILD_DIR for both deb
rm -rf "${BUILD_DIR}" || true
mkdir -p "${BUILD_DIR}"
rm -rf "${BUILD_DIR_RPM_DKMS}" || true
mkdir -p "${BUILD_DIR_RPM_DKMS}"

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
sudo mv /var/lib/dkms/lenovolegionlinux/1.0.0/deb/lenovolegionlinux-dkms_1.0.0_amd64.deb ${BUILD_DIR}
echo "Dkms deb located at ${BUILD_DIR}/lenovolegionlinux-dkms_1.0.0_amd64.deb"
##

#BUILD DKMS RPM

cd ${BUILD_DIR_RPM_DKMS}
mkdir -p rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
cp -r ${REPODIR}/kernel_module ./lenovolegionlinux-kmod-1.0.0-x86_64
sudo mv lenovolegionlinux-kmod-1.0.0-x86_64/lenovolegionlinux.spec rpmbuild/SPECS
tar --create --file lenovolegionlinux-kmod-1.0.0-x86_64.tar.gz lenovolegionlinux-kmod-1.0.0-x86_64 && rm --recursive lenovolegionlinux-kmod-1.0.0-x86_64
mv lenovolegionlinux-kmod-1.0.0-x86_64.tar.gz rpmbuild/SOURCES
cd rpmbuild && rpmbuild --define "_topdir `pwd`" -bs SPECS/lenovolegionlinux.spec
rpmbuild --nodeps --define "_topdir `pwd`" --rebuild SRPMS/dkms-lenovolegionlinux-1.0.0-0.src.rpm
mv RPMS/x86_64/dkms-lenovolegionlinux-1.0.0-0.x86_64.rpm ${BUILD_DIR}/


##BUILD PYTHON DEB
cd ${REPODIR}/python/legion_linux
sed -i "s/version = _VERSION/version = ${TAG}/g" setup.cfg

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
sudo mv ../python3-legion-linux_1.0.0-1_all.deb ${BUILD_DIR}

#Build to RPM
cd ${BUILD_DIR}
mkdir -p rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
cp -r ${REPODIR}/python/legion_linux python-lenovolegionlinux-1.0.0
mv python-lenovolegionlinux-1.0.0/lenovolegionlinux.spec rpmbuild/SPECS
rm -r python-lenovolegionlinux-1.0.0/legion_linux/extra && cp -r ${REPODIR}/extra python-lenovolegionlinux-1.0.0/legion_linux/extra
tar --create --file python-lenovolegionlinux-1.0.0.tar.gz python-lenovolegionlinux-1.0.0 && rm --recursive python-lenovolegionlinux-1.0.0
mv python-lenovolegionlinux-1.0.0.tar.gz rpmbuild/SOURCES
cd rpmbuild
rpmbuild --define "_topdir `pwd`" -bs SPECS/lenovolegionlinux.spec
rpmbuild --nodeps --define "_topdir `pwd`" --rebuild SRPMS/python-lenovolegionlinux-1.0.0-1.src.rpm
mv RPMS/noarch/python-lenovolegionlinux-1.0.0-1.noarch.rpm ${BUILD_DIR}/
