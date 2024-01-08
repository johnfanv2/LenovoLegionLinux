#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Needed in CI
sudo apt-get update

# Linter
# Tools for running GUI tests headless
sudo apt-get -y -qq install \
    wget \
    pylint python3-venv python3-pip \
    xvfb libxcb-xinerama0 libgl1-mesa-glx

sudo pip install pyqt6-tools PyQt6

${DIR}/install_dependencies_ubuntu.sh
${DIR}/linux_kernel/install_checkpath.sh
