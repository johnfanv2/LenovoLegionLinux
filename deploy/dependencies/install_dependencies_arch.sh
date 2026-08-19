#!/bin/bash
set -ex
kernel_release="$(uname -r)"
if [[ "${kernel_release}" == *-cachyos* ]]; then
    kernel_headers=linux-cachyos-headers
else
    kernel_headers=linux-headers
fi

sudo pacman -S --needed --disable-download-timeout --noconfirm \
    "${kernel_headers}" base-devel clang llvm cmake ninja git lm_sensors dmidecode \
    nlohmann-json yaml-cpp \
    python python-pyqt6 python-yaml python-argcomplete python-pillow python-darkdetect \
    python-build python-installer python-wheel python-setuptools \
    dkms openssl mokutil
