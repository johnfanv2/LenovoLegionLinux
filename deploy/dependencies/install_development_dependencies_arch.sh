#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Tools for running GUI tests headless
sudo pacman -S --noconfirm --disable-download-timeout wget \
    python3 \
    python-pylint \
    xorg-server-xvfb libxcb

${DIR}/linux_kernel/install_checkpath.sh

