#!/bin/bash
set -ex
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPODIR="${DIR}/.."

if [ "$EUID" -ne 0 ]; then
	echo "Please run as root to install"
	exit 1
fi

#Install LenovoLegionLinux python package
cd "${REPODIR}"
TAG=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/[^0-9.]*//g' || true)

# a (shallow) checkout has no tags; keep the placeholder version
if [ -z "$TAG" ]; then
	TAG=_VERSION
fi

cd "${REPODIR}/python/legion_linux"
sed -i "s/version = _VERSION/version = ${TAG}/g" setup.cfg
#mkdir $HOME/.config/lenovo_linux

# Build and install python package with build and installer
python3 -m build --wheel --no-isolation

python3 -m installer --destdir="/" dist/*.whl
#Create config folder (not overwrite old folder)
#cp -r /usr/share/legion_linux /etc/legion_linux

echo "Done"
