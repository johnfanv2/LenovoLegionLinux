#!/bin/bash
set -ex

cd /tmp
git clone https://aur.archlinux.org/lenovolegionlinux-git.git
cd lenovolegionlinux-git
makepkg -si --noconfirm

cd /tmp
git clone https://aur.archlinux.org/lenovolegionlinux-dkms-git.git
cd lenovolegionlinux-dkms-git
makepkg -si --noconfirm
