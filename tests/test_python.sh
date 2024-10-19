#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

pylint --ignore-patterns=legion_gui_qt6.py,legion_version.py --disable no-self-use --rcfile ${DIR}/../python/legion_linux/pylintrc ${DIR}/../python/legion_linux/legion_linux