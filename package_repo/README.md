[![Build](https://github.com/johnfanv2/LenovoLegionLinux/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/johnfanv2/LenovoLegionLinux/actions/workflows/build.yml)

# LenovoLegionLinux package for Ubuntu and Fedora
A PPA repository for my packages:

- [LenovoLegionLinux](https://github.com/johnfanv2/LenovoLegionLinux)
- [darkdetect (depedency)](https://github.com/albertosottile/darkdetect)

# Usage

Debian/Ubuntu:
```bash
sudo apt-get install curl gpg
sudo curl -s https:/johnfanv2.github.io/LenovoLegionLinux/package_repo/ubuntu/KEY.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/lll-ppa.gpg > /dev/null
sudo curl -SsL -o /etc/apt/sources.list.d/lll-ppa.list hhttps:/johnfanv2.github.io/LenovoLegionLinux/package_repo/ubuntu/lll-ppa.list
sudo apt update
sudo apt install lenovolegionlinux-dkms python3-darkdetect python3-legion-linux
```

Fedora/rpm base distros:

```bash
sudo curl -s https:/johnfanv2.github.io/LenovoLegionLinux/package_repo/fedora/LLL.repo | sudo tee /etc/yum.repos.d/LLL.repo > /dev/null
sudo dnf config-manager --add-repo /etc/yum.repos.d/LLL.repo
sudo dnf config-manager --set-enabled LLL-pkg-repo
sudo dnf install dkms-lenovolegionlinux python3-darkdetect python3-lenovolegionlinux
```