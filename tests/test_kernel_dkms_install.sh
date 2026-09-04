#!/bin/bash
sudo apt-get install dkms openssl mokutil
cd kernel_module || exit 1
sudo make dkms