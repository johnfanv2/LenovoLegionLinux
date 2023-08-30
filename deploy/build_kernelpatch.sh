#!/bin/bash
set -ex
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPODIR="${DIR}/.."
BUILD_DIR=/tmp/linux
TAG=$(git describe --tags --abbrev=0 | sed 's/[^0-9.]*//g')

# recreate build dir
rm -rf "${BUILD_DIR}" || true
mkdir -p "${BUILD_DIR}"

# clone
cd "${BUILD_DIR}"
git clone --depth 1 --branch v6.5 git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
cd ${BUILD_DIR}/linux
git checkout v6.5

cp ${REPODIR}/kernel_module/6_5_patch/Kconfig ${BUILD_DIR}/linux/drivers/platform/x86
cp ${REPODIR}/kernel_module/6_5_patch/Makefile ${BUILD_DIR}/linux/drivers/platform/x86
cp ${REPODIR}/kernel_module/legion-laptop.c ${BUILD_DIR}/linux/drivers/platform/x86

cd ${BUILD_DIR}/linux
git config user.name "John Martens"
git config user.email "john.martens4@proton.me"
git add --all
git commit -m "Add legion-laptop v${TAG}

Add extra support for Lenovo Legion laptops.
"
git format-patch HEAD~1

## Build
sudo apt-get install -y build-essential libncurses-dev bison flex libssl-dev libelf-dev

# clean
make clean && make mrproper

# create config with new module enabled
make defconfig
# cp -v /boot/config-$(uname -r) .config
echo "CONFIG_LEGION_LAPTOP=m" >>.config

# build
make -j 8
