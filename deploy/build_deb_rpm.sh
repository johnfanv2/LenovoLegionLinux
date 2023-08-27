#!/bin/bash
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
REPODIR="${DIR}/.."
BUILD_DIR=/tmp/pkg
BUILD_DIR_RPM_DKMS=/tmp/rpm_dkms

set -ex
#Intsall debian packages
sudo apt-get install debhelper dkms python3-all python3-stdeb dh-python alien rpm

#GET TAG (USE THIS WHEN STABLE RELEASE GET OUT)
#cd ${REPODIR_LLL}
#TAG=$(git tag --points-at HEAD | cut -c 2-)
#cd ${REPODIR}
TAG="1.0.0"
DKMSDIR=/usr/src/lenovolegionlinux-${TAG}

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
sudo sed -i "s/DKMS_VERSION/$TAG/g" ${DKMSDIR}/dkms.conf

#Build dkms
sudo dkms add -m lenovolegionlinux -v ${TAG}
sudo dkms build -m lenovolegionlinux -v ${TAG}

#Build deb file
sudo dkms mkdsc -m lenovolegionlinux -v ${TAG}
sudo dkms mkdeb -m lenovolegionlinux -v ${TAG}

#Copy deb to deploy folder
sudo mv /var/lib/dkms/lenovolegionlinux/${TAG}/deb/lenovolegionlinux-dkms_${TAG}_amd64.deb ${BUILD_DIR}
echo "Dkms deb located at ${BUILD_DIR}/lenovolegionlinux-dkms_${TAG}_amd64.deb"
##

#BUILD DKMS RPM

cd ${BUILD_DIR_RPM_DKMS}
mkdir -p rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
cp -r ${REPODIR}/kernel_module ./lenovolegionlinux-kmod-${TAG}-x86_64
mv lenovolegionlinux-kmod-${TAG}-x86_64/lenovolegionlinux.spec rpmbuild/SPECS
#Change version according to tag
sed -i "s/Version:      _VERSION/Version:      $TAG/g" rpmbuild/SPECS/lenovolegionlinux.spec
#
tar --create --file lenovolegionlinux-kmod-${TAG}-x86_64.tar.gz lenovolegionlinux-kmod-${TAG}-x86_64 && rm --recursive lenovolegionlinux-kmod-${TAG}-x86_64
mv lenovolegionlinux-kmod-${TAG}-x86_64.tar.gz rpmbuild/SOURCES
cd rpmbuild && rpmbuild --define "_topdir `pwd`" -bs SPECS/lenovolegionlinux.spec
rpmbuild --nodeps --define "_topdir `pwd`" --rebuild SRPMS/dkms-lenovolegionlinux-${TAG}-0.src.rpm
mv RPMS/x86_64/dkms-lenovolegionlinux-${TAG}-0.x86_64.rpm ${BUILD_DIR}/


##BUILD PYTHON DEB
cd ${REPODIR}/python/legion_linux
#Change version according to tag
sed -i "s/version = _VERSION/version = ${TAG}/g" setup.cfg
#

# Create package sceleton
sudo python3 setup.py --command-packages=stdeb.command sdist_dsc
cd deb_dist/legion-linux-${TAG}

##Add to debial install
sudo cp -R ../../../../extra/service/legion-linux.service .
sudo cp -R ../../../../extra/service/legion-linux.path .
echo "legion-linux.service /etc/systemd/system/" | sudo tee -a debian/install
echo "legion-linux.path /lib/systemd/system/" | sudo tee -a debian/install
sudo  EDITOR=/bin/true dpkg-source -q --commit . p1

# Build package
sudo dpkg-buildpackage -uc -us
sudo mv ../python3-legion-linux_${TAG}-1_all.deb ${BUILD_DIR}

#Build RPM PYTHON
cd ${BUILD_DIR}
mkdir -p rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
cp -r ${REPODIR}/python/legion_linux python-lenovolegionlinux-${TAG}
mv python-lenovolegionlinux-${TAG}/lenovolegionlinux.spec rpmbuild/SPECS
#Change version according to tag
sed -i "s/%define version _VERSION/%define version ${TAG}/g" rpmbuild/SPECS/lenovolegionlinux.spec
sed -i "s/%define unmangled_version _VERSION/%define unmangled_version ${TAG}/g" rpmbuild/SPECS/lenovolegionlinux.spec
#
rm -r python-lenovolegionlinux-${TAG}/legion_linux/extra && cp -r ${REPODIR}/extra python-lenovolegionlinux-${TAG}/legion_linux/extra
tar --create --file python-lenovolegionlinux-${TAG}.tar.gz python-lenovolegionlinux-${TAG} && rm --recursive python-lenovolegionlinux-${TAG}
mv python-lenovolegionlinux-${TAG}.tar.gz rpmbuild/SOURCES
cd rpmbuild
rpmbuild --define "_topdir `pwd`" -bs SPECS/lenovolegionlinux.spec
rpmbuild --nodeps --define "_topdir `pwd`" --rebuild SRPMS/python-lenovolegionlinux-${TAG}-1.src.rpm
mv RPMS/noarch/python-lenovolegionlinux-${TAG}-1.noarch.rpm ${BUILD_DIR}/
