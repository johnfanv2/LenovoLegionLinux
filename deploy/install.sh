#!/bin/bash
set -ex
cd kernel_module
sudo make reloadmodule
sudo make install