#!/bin/bash
set -ex
DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd ${DIR}/../python/legion_linux

if [ "$EUID" -ne 0 ]
  then echo "Please run as root to install"
  exit
else
    xargs rm -rf < files.txt
fi