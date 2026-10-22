#!/bin/bash
set -ex
cd kernel_module
KERNELVERSION="$(../tests/kernel_version.sh)"
make KERNELVERSION="$KERNELVERSION"
sudo make install KERNELVERSION="$KERNELVERSION"
