SHELL := /bin/bash
KERNELVERSION  ?= $(shell uname --kernel-release)
KSRC := /lib/modules/$(KERNELVERSION)/build

DKMS_VERSION ?= 1.0.0
PKG_NAME := lenovolegionlinux-dkms
PKG_ARCH := all
PKG_BUILD_DIR := /tmp/lenovolegionlinux-dkms-deb
PKG_OUTPUT_DIR := ../deploy/packages
PKG_DST := $(PKG_BUILD_DIR)/usr/src/LenovoLegionLinux-$(DKMS_VERSION)

#install dir for kernel drivers
INSTALLDIR := /lib/modules/$(KERNELVERSION)/kernel/drivers/platform/x86
MODDESTDIR := /lib/modules/$(KERNELVERSION)/kernel/drivers/platform/x86
DKMSDIR := /usr/src/LenovoLegionLinux-1.0.0

obj-m += legion-laptop.o

all:
	$(MAKE) -C $(KSRC) M=$(shell pwd) modules

moduleInContainer:
	docker run -it --rm -v "$(shell pwd)":/kernel_module -w /kernel_module  -v /usr/src/:/usr/src/  -v /lib/modules/:/lib/modules gcc:12.2.0 bash

allWarn:
	$(MAKE) -C $(KSRC) M=$(shell pwd) KCFLAGS=-W modules

clean:
	make -C $(KSRC) M=$(shell pwd) clean

install: all
	@rm --force --verbose $(INSTALLDIR)/legion-laptop.ko
	@mkdir --parent --verbose $(MODDESTDIR)
	@install --preserve-timestamps -D --mode=644 *.ko $(INSTALLDIR)
	@depmod --all $(KVER)
	@printf "%s\n" "Installion finished."

uninstall:
	@rm -f $(INSTALLDIR)/legion-laptop.ko
	@depmod --all
	@printf "%s\n" "Uninstall finished."

install_forcereload:
	make install
	make forcereloadmodule
	bash -c "./issue-warning.sh"

reloadmodule:
	rmmod legion-laptop.ko || true
	insmod legion-laptop.ko
	dmesg --ctime
	bash -c "./issue-warning.sh"

forcereloadmodule:
	rmmod legion-laptop.ko || true
	insmod legion-laptop.ko force=1
	dmesg --ctime
	bash -c "./issue-warning.sh"

forcereloadmodulereadonly:
	rmmod legion-laptop.ko || true
	insmod legion-laptop.ko force=1 ec_readonly=1
	dmesg --ctime
	bash -c "./issue-warning.sh"

reloadmodule_disableplatformprofile:
	rmmod legion-laptop.ko || true
	insmod legion-laptop.ko enable_platformprofile=0
	dmesg --ctime
	bash -c "./issue-warning.sh"

forcereloadmodule_disableplatformprofile:
	rmmod legion-laptop.ko || true
	insmod legion-laptop.ko force=1 enable_platformprofile=0
	dmesg --ctime
	bash -c "./issue-warning.sh"

dkms: all
	if [ -d $(DKMSDIR) ]; then\
    	rm --recursive $(DKMSDIR)/*;\
        cp --recursive * $(DKMSDIR)/;\
	else \
		mkdir --verbose $(DKMSDIR);\
        cp --recursive * $(DKMSDIR);\
		dkms add -m LenovoLegionLinux -v 1.0.0;\
	fi
	dkms build LenovoLegionLinux --force -v 1.0.0
	dkms install LenovoLegionLinux --force -v 1.0.0
	printf "%s\n" "Loading module"
	modprobe legion_laptop
	dmesg --ctime | grep legion_laptop
	bash -c "./issue-warning.sh"

deb:
	@command -v dpkg-deb >/dev/null 2>&1 || { \
		echo "dpkg-deb not found; install dpkg-dev first"; \
		exit 1; \
	}
	@rm -rf $(PKG_BUILD_DIR)
	@mkdir -p $(PKG_BUILD_DIR)/DEBIAN $(PKG_DST) $(PKG_OUTPUT_DIR)
	@rsync -a --delete \
		--exclude='*.ko' \
		--exclude='*.mod' \
		--exclude='*.mod.c' \
		--exclude='*.o' \
		--exclude='Module.symvers' \
		--exclude='modules.order' \
		. $(PKG_DST)/
	@sed -i 's/PACKAGE_VERSION="DKMS_VERSION"/PACKAGE_VERSION="$(DKMS_VERSION)"/' $(PKG_DST)/dkms.conf
	@printf '%s\n' \
		"Package: $(PKG_NAME)" \
		"Version: $(DKMS_VERSION)" \
		"Section: kernel" \
		"Priority: optional" \
		"Architecture: $(PKG_ARCH)" \
		"Maintainer: Lenovo Legion Linux Team <noreply@example.com>" \
		"Depends: dkms" \
		"Description: LenovoLegionLinux DKMS package" \
		" DKMS wrapper for Lenovo Legion kernel module." \
		> $(PKG_BUILD_DIR)/DEBIAN/control
	@printf '%s\n' \
		"#!/bin/sh" \
		"set -e" \
		"dkms add -m LenovoLegionLinux -v $(DKMS_VERSION) -q || true" \
		"dkms build -m LenovoLegionLinux -v $(DKMS_VERSION) -q || true" \
		"dkms install -m LenovoLegionLinux -v $(DKMS_VERSION) -q --force || true" \
		"exit 0" \
		> $(PKG_BUILD_DIR)/DEBIAN/postinst
	@printf '%s\n' \
		"#!/bin/sh" \
		"set -e" \
		"dkms remove -m LenovoLegionLinux -v $(DKMS_VERSION) -q --all || true" \
		"exit 0" \
		> $(PKG_BUILD_DIR)/DEBIAN/prerm
	@chmod 0755 $(PKG_BUILD_DIR)/DEBIAN/postinst $(PKG_BUILD_DIR)/DEBIAN/prerm
	@dpkg-deb --build $(PKG_BUILD_DIR) $(PKG_OUTPUT_DIR)/$(PKG_NAME)_$(DKMS_VERSION)_$(PKG_ARCH).deb
	@rm -rf $(PKG_BUILD_DIR)
	@printf "Built %s\n" "$(PKG_OUTPUT_DIR)/$(PKG_NAME)_$(DKMS_VERSION)_$(PKG_ARCH).deb"
