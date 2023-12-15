!/bin/bash
set -ex
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPODIR="${DIR}"

cd ${REPODIR}/python/legion_linux

if [ "$EUID" -ne 0 ]; then
	echo "Please run as root to install"
	exit
fi

rm /usr/share/applications/legion_gui.desktop
rm /usr/share/applications/legion_gui_user.desktop
rm /usr/share/icons/legion_logo.png
rm /usr/share/polkit-1/actions/legion_cli.policy
rm /usr/share/polkit-1/actions/legion_gui.policy
sudo pip3 uninstall legion_linux
