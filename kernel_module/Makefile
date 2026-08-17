SHELL := /bin/bash
KERNELVERSION  ?= $(shell uname -r)
KSRC := /lib/modules/$(KERNELVERSION)/build

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
	@rm -fv $(INSTALLDIR)/legion-laptop.ko
	@mkdir -pv $(MODDESTDIR)
	@install -p -D -m 644 *.ko $(INSTALLDIR)
	@depmod -a $(KVER)
	@printf "%s\n" "Installion finished."

uninstall:
	@rm -f $(INSTALLDIR)/legion-laptop.ko
	@depmod -a
	@printf "%s\n" "Uninstall finished."

install_forcereload:
	make install
	make forcereloadmodule
	bash -c "./issue-warning.sh"

reloadmodule:
	rmmod legion_laptop 2>/dev/null || true
	# insmod does not resolve dependencies; load them first
	modprobe wmi 2>/dev/null || true
	modprobe platform_profile 2>/dev/null || true
	insmod legion-laptop.ko
	dmesg
	bash -c "./issue-warning.sh"

forcereloadmodule:
	rmmod legion_laptop 2>/dev/null || true
	# insmod does not resolve dependencies; load them first
	modprobe wmi 2>/dev/null || true
	modprobe platform_profile 2>/dev/null || true
	insmod legion-laptop.ko force=1
	dmesg
	bash -c "./issue-warning.sh"

forcereloadmodulereadonly:
	rmmod legion_laptop 2>/dev/null || true
	# insmod does not resolve dependencies; load them first
	modprobe wmi 2>/dev/null || true
	modprobe platform_profile 2>/dev/null || true
	insmod legion-laptop.ko force=1 ec_readonly=1
	dmesg
	bash -c "./issue-warning.sh"

reloadmodule_disableplatformprofile:
	rmmod legion_laptop 2>/dev/null || true
	# insmod does not resolve dependencies; load them first
	modprobe wmi 2>/dev/null || true
	modprobe platform_profile 2>/dev/null || true
	insmod legion-laptop.ko enable_platformprofile=0
	dmesg
	bash -c "./issue-warning.sh"

forcereloadmodule_disableplatformprofile:
	rmmod legion_laptop 2>/dev/null || true
	# insmod does not resolve dependencies; load them first
	modprobe wmi 2>/dev/null || true
	modprobe platform_profile 2>/dev/null || true
	insmod legion-laptop.ko force=1 enable_platformprofile=0
	dmesg
	bash -c "./issue-warning.sh"

dkms: all
	if [ -d $(DKMSDIR) ]; then\
    	rm -r $(DKMSDIR)/*;\
        cp -r * $(DKMSDIR)/;\
	else \
		mkdir -v $(DKMSDIR);\
        cp -r * $(DKMSDIR);\
		dkms add -m LenovoLegionLinux -v 1.0.0;\
	fi
	dkms build LenovoLegionLinux --force -v 1.0.0
	dkms install LenovoLegionLinux --force -v 1.0.0
	printf "%s\n" "Loading module"
	modprobe legion_laptop
	dmesg | grep legion_laptop
	bash -c "./issue-warning.sh"
