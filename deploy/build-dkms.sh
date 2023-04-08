#!/bin/bash
if [[ $(/usr/bin/id -u) -ne 0 ]]; then
    echo "Run as superuser"
    exit 1
fi

set -ex
cd ..
cd kernel_module

#Copy folder for dkms
if [ -d /usr/src/LenovoLegionLinux-1.0.0 ]; then
	rm -r /usr/src/LenovoLegionLinux-1.0.0/*
	cp -r * /usr/src/LenovoLegionLinux-1.0.0/
else
    mkdir /usr/src/LenovoLegionLinux-1.0.0
    cp -r * /usr/src/LenovoLegionLinux-1.0.0
    dkms add -m LenovoLegionLinux -v 1.0.0
fi

#Build and install as dkms module
dkms build LenovoLegionLinux --force -v 1.0.0
dkms install LenovoLegionLinux --force -v 1.0.0

#load the module
modprobe legion_laptop
dmesg | grep legion_laptop
