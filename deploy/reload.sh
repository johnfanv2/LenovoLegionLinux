#!/bin/bash
set -ex
cd kernel_module
make

find /lib/modules/$(uname -r) -type f -name '*.ko'
sudo modprobe wmi || true 
sudo modprobe platform_profile || true
sudo make reloadmodule || true
sudo dmesg