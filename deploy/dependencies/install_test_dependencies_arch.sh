#!/bin/bash
set -ex
sudo pacman -S --noconfirm --disable-download-timeout linux-headers git xorg-server-xvfb libxcb base-devel dkms i2c-tools dmidecode fakeroot