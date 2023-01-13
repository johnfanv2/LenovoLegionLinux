#!/bin/bash
set -ex
cd kernel_module
make
sudo make reloadmodule || true
sudo dmesg