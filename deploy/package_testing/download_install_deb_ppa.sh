#!/bin/bash
sudo apt-get install -y curl gpg
sudo curl -s https://MrDuartePT.github.io/LLL-pkg-repo/ubuntu/KEY.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/lll-ppa.gpg > /dev/null
sudo curl -SsL -o /etc/apt/sources.list.d/lll-ppa.list https://MrDuartePT.github.io/LLL-pkg-repo/ubuntu/lll-ppa.list
sudo apt update
sudo apt install -y lenovolegionlinux-dkms python3-legion-linux