#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Smoketest CLI
"${DIR}/../python/legion_linux/legion_linux/legion_cli.py" --donotexpecthwmon
