cd /tmp

# Build libepoxy
git clone https://github.com/anholt/libepoxy.git
cd libepoxy
meson -Dprefix=/usr build
sudo ninja -C build/ install
cd ..

#Build xwayland
git clone https://gitlab.freedesktop.org/xorg/xserver.git
cd xserver
meson -Dprefix=/usr -Dxorg=false -Dxwayland=true -Dxvfb=false \
	-Dxnest=false -Dxquartz=false -Dxwin=false -Ddocs=false build
sudo ninja -C build/ install
cd ..
