#!/bin/bash
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPODIR="${DIR}/.."
set -ex
${DIR}/test_python_cli_installed.sh
${DIR}/test_python_gui_installed.sh 