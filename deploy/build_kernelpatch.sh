#!/bin/bash
set -ex
KERNEL_VERSION="6.10"
KERNEL_VERSION_UNDERSCORE="${KERNEL_VERSION//./_}"
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPODIR="${DIR}/.."
BUILD_DIR="/tmp/linux"
TAG=$(git describe --tags --abbrev=0 | sed 's/[^0-9.]*//g')

echo "Build parameter:"
echo "KERNEL_VERSION: ${KERNEL_VERSION}"
echo "KERNEL_VERSION_UNDERSCORE: ${KERNEL_VERSION_UNDERSCORE}"
echo "DIR: ${DIR}"
echo "REPODIR: ${REPODIR}"
echo "BUILD_DIR: ${BUILD_DIR}"
echo "TAG: ${TAG}"

# Recreate build dir
rm -rf "${BUILD_DIR}" || true
mkdir -p "${BUILD_DIR}"

# Clone
cd "${BUILD_DIR}"
git clone --depth 1 --branch "v${KERNEL_VERSION}" git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
cd ${BUILD_DIR}/linux
git checkout "v${KERNEL_VERSION}"

cp ${REPODIR}/kernel_module/${KERNEL_VERSION_UNDERSCORE}_patch/Kconfig ${BUILD_DIR}/linux/drivers/platform/x86
cp ${REPODIR}/kernel_module/${KERNEL_VERSION_UNDERSCORE}_patch/Makefile ${BUILD_DIR}/linux/drivers/platform/x86
cp ${REPODIR}/kernel_module/legion-laptop.c ${BUILD_DIR}/linux/drivers/platform/x86

cd ${BUILD_DIR}/linux
git config user.name "John Martens"
git config user.email "john.martens4@proton.me"
git add --all
git commit -m "Add legion-laptop v${TAG}

Add extra support for Lenovo Legion laptops.
"
git format-patch HEAD~1

## Dependencies for building
sudo apt-get install -y build-essential libncurses-dev bison flex libssl-dev libelf-dev

# Clean
make clean && make mrproper

# Create config with new module enabled
make defconfig
# cp -v /boot/config-$(uname -r) .config
echo "CONFIG_LEGION_LAPTOP=m" >>.config

# Build
make -j 8
