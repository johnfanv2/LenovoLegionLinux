#!/bin/bash
set -ex
sudo apt-get install dkms openssl mokutil
cd kernel_module
sudo make dkms