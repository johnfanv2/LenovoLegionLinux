#!/bin/bash
sudo dnf makecache
# Tools for running GUI tests headless
sudo dnf -y install wget \
    xorg-x11-server-Xvfb libxcb