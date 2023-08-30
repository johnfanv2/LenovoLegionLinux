#!/bin/bash
cd /tmp
apt-get update && apt-get install -y wget
wget https://github.com/johnfanv2/LenovoLegionLinux/releases/download/v0.0.4-prerelease/python3-legion-linux_1.0.0-1_amd64.deb
apt-get install -y ./python3-legion-linux_1.0.0-1_amd64.deb
legion_cli
legion_gui
wget  https://github.com/johnfanv2/LenovoLegionLinux/releases/download/v0.0.2-prerelease/lenovolegionlinux-dkms_1.0.0_amd64.deb