#!/bin/bash
set -ex
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPODIR="${DIR}/.."

#Install LenovoLegionLinux python package
cd ${REPODIR}
TAG=$(git describe --tags --abbrev=0 | sed 's/[^0-9.]*//g')

cd ${REPODIR}/python/legion_linux
sed -i "s/version = _VERSION/version = ${TAG}/g" setup.cfg
#mkdir $HOME/.config/lenovo_linux

# Build and install python package with build and installer
python3 -m build --wheel --no-isolation

if [ "$EUID" -ne 0 ]; then
	echo "Please run as root to install"
	exit
else
	python3 -m installer --destdir="/" dist/*.whl
	#Create config folder (not overwrite old folder)
	#cp -r /usr/share/legion_linux /etc/legion_linux
fi

echo "Done"
