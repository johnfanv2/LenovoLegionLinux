#!/bin/bash
set -ex
KERNEL_VERSION="${KERNEL_VERSION:-$(curl -fsSL https://www.kernel.org/releases.json | python3 -c 'import json, sys; print(json.load(sys.stdin)["latest_stable"]["version"])')}"
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPODIR="${DIR}/.."
BUILD_DIR="/tmp/linux"
TAG=$(git describe --tags --abbrev=0 | sed 's/[^0-9.]*//g')

echo "Build parameter:"
echo "KERNEL_VERSION: ${KERNEL_VERSION}"
echo "DIR: ${DIR}"
echo "REPODIR: ${REPODIR}"
echo "BUILD_DIR: ${BUILD_DIR}"
echo "TAG: ${TAG}"

# Recreate build dir
rm -rf "${BUILD_DIR}" || true
mkdir -p "${BUILD_DIR}"

# Clone
cd "${BUILD_DIR}"
git clone --depth 1 --branch "v${KERNEL_VERSION}" https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
cd ${BUILD_DIR}/linux

DRIVER_DIR="${BUILD_DIR}/linux/drivers/platform/x86"
if [ -d "${DRIVER_DIR}/lenovo" ]; then
	DRIVER_DIR="${DRIVER_DIR}/lenovo"
fi
if grep -q '^config LEGION_LAPTOP$' "${DRIVER_DIR}/Kconfig"; then
	echo "CONFIG_LEGION_LAPTOP already exists in Linux ${KERNEL_VERSION}"
	exit 1
fi

cp "${REPODIR}/kernel_module/legion-laptop.c" "${DRIVER_DIR}/legion-laptop.c"
cat >> "${DRIVER_DIR}/Kconfig" <<'EOF'

config LEGION_LAPTOP
	tristate "Lenovo Legion Laptop Extras"
	depends on ACPI
	depends on ACPI_WMI || ACPI_WMI = n
	depends on HWMON || HWMON = n
	select ACPI_PLATFORM_PROFILE
	help
	  This is a driver for Lenovo Legion laptops and contains drivers for
	  hotkey, fan control, and power mode.
EOF
printf '\nobj-$(CONFIG_LEGION_LAPTOP) += legion-laptop.o\n' >> "${DRIVER_DIR}/Makefile"

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
