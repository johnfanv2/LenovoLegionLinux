#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

${DIR}/install_dependencies_ubuntu.sh
${DIR}/linux_kernel/install_checkpath.sh
sudo apt-get install pylint