#!/bin/bash
set -ex
sudo apt-get update
sudo apt-get install make gcc linux-headers-$(uname -r) build-essential git lm-sensors