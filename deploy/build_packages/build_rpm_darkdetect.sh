#!/bin/bash
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPODIR="${DIR}/../.."
BUILD_DIR=/tmp/darkdetect_rpm

set -ex

#Intsall fedora packages
sudo dnf install rpmdevtools rpm dkms python-devel python-setuptools python-wheel python-installer sed rpm createrepo_c python-pyyaml -y

#GET TAG
cd ${REPODIR}/subprojects/darkdetect
TAG=$(git describe --tags --abbrev=0 | sed 's/[^0-9.]*//g')

# recreate BUILD_DIR
rm -rf "${BUILD_DIR}" || true
mkdir -p "${BUILD_DIR}"

## BUILD PYTHON RPM
#Setup BUILD_DIR
cp --recursive ${REPODIR}/subprojects/darkdetect ${BUILD_DIR}/python-darkdetect-${TAG}
cp --recursive ${REPODIR}/deploy/build_packages/{setup.cfg,setup.py,darkdetect.spec} ${BUILD_DIR}/python-darkdetect-${TAG}

#Create rpm
cd ${BUILD_DIR}
mkdir -p rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
mv python-darkdetect-${TAG}/darkdetect.spec rpmbuild/SPECS
#Change version according to tag
sed -i "s/version = _VERSION/version = ${TAG}/g" python-darkdetect-${TAG}/setup.cfg
sed -i "s/%define version _VERSION/%define version ${TAG}/g" rpmbuild/SPECS/darkdetect.spec
sed -i "s/%define unmangled_version _VERSION/%define unmangled_version ${TAG}/g" rpmbuild/SPECS/darkdetect.spec
#
tar --create --file python-darkdetect-${TAG}.tar.gz python-darkdetect-${TAG} && rm --recursive python-darkdetect-${TAG}
mv python-darkdetect-${TAG}.tar.gz rpmbuild/SOURCES
cd rpmbuild

#Use distrobox to build rpm on fedora
sudo rpmbuild --define "_topdir $(pwd)" -bs SPECS/darkdetect.spec
sudo rpmbuild --define "_topdir $(pwd)" --rebuild SRPMS/python-darkdetect-${TAG}-1.src.rpm
mv RPMS/noarch/python-darkdetect-${TAG}-1.noarch.rpm ${BUILD_DIR}/

#Test Install
rpm -i ${BUILD_DIR}/python-darkdetect-${TAG}-1.noarch.rpm

#Move to repo
cp ${BUILD_DIR}/python-darkdetect-${TAG}-1.noarch.rpm ${REPODIR}/package_repo/fedora/packages
