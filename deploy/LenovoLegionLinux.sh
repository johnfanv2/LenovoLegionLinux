#!/bin/bash
#This script find if you have any aur helper and reinstall the package for you

if [[ /mnt/usr/bin/yay ]] then; # you use yay
    yay lenovolegionlinux-git
elif [[ /mnt/usr/bin/paru ]] then; # you use paru
    paru lenovolegionlinux-git
else
    echo "No aur helper detected"
    echo "reinstall the lenovolegionlinux-git manually or install aur helper (supported: yay and paru)"
