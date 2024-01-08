#!/bin/bash
set -ex
sudo pacman -S --disable-download-timeout --noconfirm linux-headers base-devel lm_sensors git dmidecode python-pyqt6 python-yaml python-argcomplete polkit python-build python-installer python-wheel python-setuptools
sudo pacman -S --disable-download-timeout --noconfirm dkms openssl mokutil
