#!/bin/bash
set -ex
DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

export PYTHONPATH="${DIR}/../python/legion_linux${PYTHONPATH:+:${PYTHONPATH}}"
export QT_QPA_PLATFORM=offscreen
python3 -m unittest discover -s "${DIR}/../python/legion_linux/tests" -v
python3 -m unittest discover -s "${DIR}" -p 'test_*.py' -v
