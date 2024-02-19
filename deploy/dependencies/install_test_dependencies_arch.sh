#!/bin/bash
set -ex
sudo pacman -S --noconfirm --disable-download-timeout linux-headers git weston xwayland base-devel dkms i2c-tools dmidecode fakeroot meson
