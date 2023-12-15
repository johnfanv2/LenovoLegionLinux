#!/bin/bash
set -ex
cd kernel_module
# make

# find /lib/modules/$(uname -r) -type f -name '*.ko'
# sudo modprobe wmi || true 
# sudo modprobe platform_profile || true
# sudo dmesg

#!/bin/bash
for i in {1..20}
do
   sudo make reloadmodule || true
   echo "Reloaded $i times"
   sleep 2
done