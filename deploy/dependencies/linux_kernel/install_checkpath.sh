#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd ${DIR}/../install_dir

wget "https://raw.githubusercontent.com/torvalds/linux/master/scripts/checkpatch.pl"
wget "https://raw.githubusercontent.com/torvalds/linux/master/scripts/spelling.txt"

chmod 755 "checkpatch.pl"