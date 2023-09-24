#!/bin/bash
#!/bin/bash
set -ex
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPODIR="${DIR}/.."

#Install python darkdetect
cp --recursive ${REPODIR}/deploy/build_packages/{setup.cfg,setup.py} ${REPODIR}/subprojects/darkdetect
cd ${REPODIR}/subprojects/darkdetect

TAG=$(git describe --tags --abbrev=0 | sed 's/[^0-9.]*//g')
sed -i "s/version = _VERSION/version = ${TAG}/g" setup.cfg

python3 -m pip install --upgrade build installer
python3 -m build

if [ "$EUID" -ne 0 ]; then
	echo "Please run as root to install"
	exit
else
	python3 -m installer --destdir="/" dist/*.whl
fi

#Install LenovoLegionLinux python package
cd ${REPODIR}
TAG=$(git describe --tags --abbrev=0 | sed 's/[^0-9.]*//g')

cd ${REPODIR}/python/legion_linux
sed -i "s/version = _VERSION/version = ${TAG}/g" setup.cfg

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
