#!/bin/bash
cd /tmp
git clone https://gitlab.freedesktop.org/ofourdan/xwayland-run.git
cd xwayland-run
meson setup --prefix=/usr -Dcompositor=weston . build
sudo meson install -C build

#Fix wlheadless module not found
export PYTHONPATH="${PYTHONPATH}:/usr/local/lib/python3/dist-packages"
