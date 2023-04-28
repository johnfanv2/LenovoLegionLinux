#!/bin/bash
set -ex
sudo pacman -S --noconfirm linux-headers base-devel lm_sensors git dmidecode python-pyqt5 python-yaml python-argcomplete polkit python-build python-installer python-wheel python-setuptools
sudo pacman -S --noconfirm dkms openssl mokutil