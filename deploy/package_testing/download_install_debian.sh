#!/bin/bash
set -ex
sudo apt install -y curl

# deb.debian.org has a valid TLS certificate; ftp.de.debian.org serves a
# mismatching one (curl error 60). -f makes curl fail loudly instead of
# leaving an empty file for apt to reject with a confusing error.
sudo curl -fsS https://deb.debian.org/debian/pool/main/l/lenovolegionlinux/lenovolegionlinux-dkms_0.0.20+ds-1.1_amd64.deb -o /tmp/lenovolegionlinux-dkms_0.0.20+ds-1.1_amd64.deb
sudo curl -fsS https://deb.debian.org/debian/pool/main/l/lenovolegionlinux/python3-legion-linux_0.0.20+ds-1.1_all.deb -o /tmp/python3-legion-linux_0.0.20+ds-1.1_all.deb
sudo curl -fsS https://deb.debian.org/debian/pool/main/l/lenovolegionlinux/legiond_0.0.20+ds-1.1_amd64.deb -o /tmp/legiond_0.0.20+ds-1.1_amd64.deb

sudo apt install -y /tmp/lenovolegionlinux-dkms_0.0.20+ds-1.1_amd64.deb
sudo apt install -y /tmp/python3-legion-linux_0.0.20+ds-1.1_all.deb
sudo apt install -y /tmp/legiond_0.0.20+ds-1.1_amd64.deb
