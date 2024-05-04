#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

sudo dnf makecache
# Tools for running GUI tests headless
sudo dnf -y install wget \
    python3 python3-installer python3-build \
    xorg-x11-server-Xvfb libxcb
# Linter/Tests (not as package in all rhel variants available!)
python3 -m pip install pytest pylint

${DIR}/linux_kernel/install_checkpath.sh

