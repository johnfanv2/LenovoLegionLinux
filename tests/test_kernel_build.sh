#!/bin/bash
set -ex
cd kernel_module
make KERNELVERSION="$(../tests/kernel_version.sh)"
