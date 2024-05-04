#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# refresh, otherwise sometimes we get "digest failure" because mirror/version changed from last time
sudo zypper refresh 

# Linter
# Tools for running GUI tests headless
# install directly from package file because which dependency broken
sudo rpm -i --nodeps https://download.opensuse.org/repositories/openSUSE:/Factory/standard/noarch/xvfb-run-1.5.2-7.2.noarch.rpm
# sudo zypper -n install --force --best-effort xvfb-run
sudo zypper --non-interactive install \
    wget \
    python3-pylint python3-installer python3-build \
    xorg-x11-server-extra libxcb-xinerama0 xauth


${DIR}/linux_kernel/install_checkpath.sh
