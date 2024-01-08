#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Needed in CI
sudo apt-get update

# Linter
# Tools for running GUI tests headless
sudo apt-get -y -qq install \
    wget \
    pylint pyqt6-dev-tools python3-venv \
    xvfb libxcb-xinerama0

${DIR}/install_dependencies_ubuntu.sh
${DIR}/linux_kernel/install_checkpath.sh
