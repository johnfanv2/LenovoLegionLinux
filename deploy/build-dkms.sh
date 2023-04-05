#!/bin/bash
if [[ $(/usr/bin/id -u) -ne 0 ]]; then
    echo "Run as superuser"
    exit
else
    set -ex
    cd ..
    cd kernel_module

    #Copy folder for dkms
    if [ -d "/usr/src/LenovoLegionLinux-9999" ]; then
        rm -r /usr/src/LenovoLegionLinux-9999
    fi
    mkdir /usr/src/LenovoLegionLinux-9999
    cp -r * /usr/src/LenovoLegionLinux-9999

    #Build and install as dkms module
    dkms build LenovoLegionLinux --force -v 9999
    dkms install LenovoLegionLinux --force -v 9999
fi