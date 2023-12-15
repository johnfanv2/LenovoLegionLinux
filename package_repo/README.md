
<h1 align="left">
  <a href="https://github.com/johnfanv2/LenovoLegionLinux" target="_blank">
    <picture>
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/johnfanv2/LenovoLegionLinux/HEAD/doc/assets/legion_logo_dark.svg">
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/johnfanv2/LenovoLegionLinux/HEAD/doc/assets/legion_logo_light.svg">
      <img alt="LenovoLegionLinux" src="https://raw.githubusercontent.com/johnfanv2/LenovoLegionLinux/HEAD/doc/assets/legion_logo_dark.svg" height="50" style="max-width: 100%;">
    </picture>
  </a>
    <strong> LenovoLegionLinux package for Ubuntu </strong>
</h1>

[![Build](https://github.com/johnfanv2/LenovoLegionLinux/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/johnfanv2/LenovoLegionLinux/actions/workflows/build.yml)
[![Join Discord](https://img.shields.io/discord/761178912230473768?label=Legion%20Series%20Discord)](https://discord.com/invite/legionseries)
[![Check Reddit](https://img.shields.io/static/v1?label=Reddit&message=LenovoLegion&color=green)](https://www.reddit.com/r/LenovoLegion/)
[![More Reddit](https://img.shields.io/static/v1?label=Reddit&message=linuxhardware&color=blueviolet)](https://www.reddit.com/r/linuxhardware/)
</br>
[![Unbutu and Debian PPA](https://img.shields.io/badge/Ubuntu%2FDebian-LLL_PPA-orange)](https://github.com/johnfanv2/LenovoLegionLinux/tree/main/package_repo)
[![Fedora Copr](https://img.shields.io/badge/Nobara%2FFedora-fedora_copr-blue)](https://copr.fedorainfracloud.org/coprs/mrduarte/LenovoLegionLinux/)

A PPA repository for my packages:

- [LenovoLegionLinux](https://github.com/johnfanv2/LenovoLegionLinux)
- [darkdetect (depedency)](https://github.com/albertosottile/darkdetect)

# Usage

Debian/Ubuntu:
```bash
sudo apt-get install curl gpg
sudo curl -s https://johnfanv2.github.io/LenovoLegionLinux/package_repo/ubuntu/KEY.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/lll-ppa.gpg > /dev/null
sudo curl -SsL -o /etc/apt/sources.list.d/lll-ppa.list https://johnfanv2.github.io/LenovoLegionLinux/package_repo/ubuntu/lll-ppa.list
sudo apt update
sudo apt install lenovolegionlinux-dkms python3-darkdetect python3-legion-linux
```

Fedora packages was moved to copr
Remove Fedora repo before using copr:
```bash
sudo dnf uninstall dkms-lenovolegionlinux python-darkdetect python-lenovolegionlinux
sudo dnf config-manager --set-disabled LLL-pkg-repo
rm /etc/yum.repos.d/LLL.repo
```

Fedora copr link: https://copr.fedorainfracloud.org/coprs/mrduarte/LenovoLegionLinux/