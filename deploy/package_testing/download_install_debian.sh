sudo apt install -y curl

sudo curl --insecure https://ftp.de.debian.org/debian/pool/main/l/lenovolegionlinux/lenovolegionlinux-dkms_0.0.20+ds-1.1_amd64.deb -o /tmp/lenovolegionlinux-dkms_0.0.20+ds-1.1_amd64.deb
sudo curl --insecure https://ftp.de.debian.org/debian/pool/main/l/lenovolegionlinux/python3-legion-linux_0.0.20+ds-1.1_all.deb -o /tmp/python3-legion-linux_0.0.20+ds-1.1_all.deb
sudo curl --insecure https://ftp.de.debian.org/debian/pool/main/l/lenovolegionlinux/legiond_0.0.20+ds-1.1_amd64.deb -o /tmp/legiond_0.0.20+ds-1.1_amd64.deb

sudo apt install -y /tmp/lenovolegionlinux-dkms_0.0.20+ds-1.1_amd64.deb
sudo apt install -y /tmp/python3-legion-linux_0.0.20+ds-1.1_all.deb
sudo apt install -y /tmp/legiond_0.0.20+ds-1.1_amd64.deb
