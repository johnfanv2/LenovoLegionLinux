#!/bin/bash
set -ex
# refresh, otherwise sometimes we get "digest failure" because mirror/version changed from last time
sudo zypper refresh 
sudo zypper --non-interactive install make gcc kernel-devel kernel-default-devel git libopenssl-devel sensors dmidecode python3-qt5 python3-pip python3-PyYAML
sudo zypper --non-interactive install python3-argcomplete 