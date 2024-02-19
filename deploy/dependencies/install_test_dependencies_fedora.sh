#!/bin/bash
sudo dnf makecache
# Tools for running GUI tests headless
sudo dnf -y install wget \
    weston xwayland meson
