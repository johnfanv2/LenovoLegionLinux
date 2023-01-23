#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

${DIR}/install_dependencies_ubuntu.sh
${DIR}/linux_kernel/install_checkpath.sh
# Linter
sudo apt-get install pylint
# Tools for running GUI tests headless
sudo apt-get -qq install xvfb libxcb-xinerama0 pyqt5-dev-tools python3-venv