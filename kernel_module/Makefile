SHELL := /bin/bash
KERNELVERSION  ?= $(shell uname --kernel-release)
KSRC := /lib/modules/$(KERNELVERSION)/build

#install dir for kernel drivers
INSTALLDIR := /lib/modules/$(KERNELVERSION)/kernel/drivers/platform/x86
MODDESTDIR := /lib/modules/$(KERNELVERSION)/kernel/drivers/platform/x86
DKMSDIR := /usr/src/LenovoLegionLinux-1.0.0

obj-m += legion-laptop.o

all:
	$(MAKE) -C $(KSRC) M=$(shell pwd) modules
	bash -c "./issue-warning.sh"

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
	bash -c "./issue-warning.sh"

uninstall:
	@rm -f $(INSTALLDIR)/legion-laptop.ko
	@depmod --all
	@printf "%s\n" "Uninstall finished."
	bash -c "./issue-warning.sh"

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
