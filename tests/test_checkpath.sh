#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

${DIR}/../deploy/dependencies/install_dir/checkpatch.pl -f --no-tree kernel_module/legion-laptop.c