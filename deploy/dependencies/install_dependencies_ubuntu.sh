#!/bin/bash
set -ex
sudo apt-get update
sudo apt-get install -y make gcc linux-headers-$(uname -r) build-essential git lm-sensors wget python3-pyqt5 python3-yaml python3-venv python3-pip