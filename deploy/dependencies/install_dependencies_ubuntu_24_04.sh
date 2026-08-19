#!/bin/bash
set -ex
sudo apt-get update
sudo apt-get install -y make gcc g++ clang cmake ninja-build linux-headers-$(uname -r) linux-modules-extra-$(uname -r) build-essential git lm-sensors wget nlohmann-json3-dev libyaml-cpp-dev python3-pyqt6 python3-yaml python3-venv python3-pip python3-wheel python3-argcomplete
sudo apt-get install -y dkms openssl mokutil python3-pillow
