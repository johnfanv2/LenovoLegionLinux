#!/bin/bash
sudo curl -s https://MrDuartePT.github.io/LLL-pkg-repo/fedora/LLL.repo | sudo tee /etc/yum.repos.d/LLL.repo > /dev/null
sudo dnf config-manager --add-repo /etc/yum.repos.d/LLL.repo
sudo dnf config-manager --set-enabled LLL-pkg-repo
sudo dnf install -y dkms-lenovolegionlinux python-lenovolegionlinux
