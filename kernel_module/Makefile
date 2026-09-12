SHELL := /bin/bash
KERNELVERSION  ?= $(shell uname -r)
KSRC := /lib/modules/$(KERNELVERSION)/build

# Kernels built with clang (CONFIG_CC_IS_CLANG=y, e.g. CachyOS) need the LLVM
# toolchain for out-of-tree modules: gcc rejects the kernel's clang-only flags.
# Detect it so that plain `make`, `make install` and DKMS (dkms.conf runs this
# Makefile) work; override with LLVM=1 / LLVM=0 on the command line. dkms >= 3.x
# does the same detection for the build command it runs itself.
ifeq ($(shell grep -qs '^CONFIG_CC_IS_CLANG=y' $(KSRC)/include/config/auto.conf $(KSRC)/.config && echo 1),1)
LLVM ?= 1
endif
# LLVM is always passed explicitly: make exports the variable to the sub-make
# through MAKEOVERRIDES, so an empty value is needed for LLVM=0 to take effect.
KMAKEFLAGS := -C $(KSRC) M=$(CURDIR) $(if $(filter-out 0,$(LLVM)),LLVM=$(LLVM),LLVM=)

#install dir for kernel drivers
INSTALLDIR := /lib/modules/$(KERNELVERSION)/kernel/drivers/platform/x86
MODDESTDIR := /lib/modules/$(KERNELVERSION)/kernel/drivers/platform/x86
DKMSDIR := /usr/src/LenovoLegionLinux-1.0.0

obj-m += legion-laptop.o

all:
	$(MAKE) $(KMAKEFLAGS) modules

moduleInContainer:
	docker run -it --rm -v "$(shell pwd)":/kernel_module -w /kernel_module  -v /usr/src/:/usr/src/  -v /lib/modules/:/lib/modules gcc:12.2.0 bash

allWarn:
	$(MAKE) $(KMAKEFLAGS) KCFLAGS=-W modules

clean:
	$(MAKE) $(KMAKEFLAGS) clean

install: all
	@rm -fv $(INSTALLDIR)/legion-laptop.ko
	@mkdir -pv $(MODDESTDIR)
	@install -p -D -m 644 *.ko $(INSTALLDIR)
	@depmod -a $(KERNELVERSION)
	@printf "%s\n" "Installion finished."

uninstall:
	@rm -f $(INSTALLDIR)/legion-laptop.ko
	@depmod -a $(KERNELVERSION)
	@printf "%s\n" "Uninstall finished."

install_forcereload:
	make install
	make forcereloadmodule
	bash -c "./issue-warning.sh"

# insmod does not resolve module dependencies (wmi, platform_profile,
# led-class, ... vary per kernel) - load them explicitly before inserting.
define load_deps
	@for m in $$(modinfo -F depends legion-laptop.ko 2>/dev/null | tr ',' ' '); do modprobe $$m 2>/dev/null || true; done
endef

reloadmodule:
	rmmod legion_laptop 2>/dev/null || true
	$(load_deps)
	insmod legion-laptop.ko || { dmesg | tail -15; exit 1; }
	@dmesg | grep -i legion | tail -5 || true
	bash -c "./issue-warning.sh"

forcereloadmodule:
	rmmod legion_laptop 2>/dev/null || true
	$(load_deps)
	insmod legion-laptop.ko force=1 || { dmesg | tail -15; exit 1; }
	@dmesg | grep -i legion | tail -5 || true
	bash -c "./issue-warning.sh"

forcereloadmodulereadonly:
	rmmod legion_laptop 2>/dev/null || true
	$(load_deps)
	insmod legion-laptop.ko force=1 ec_readonly=1 || { dmesg | tail -15; exit 1; }
	@dmesg | grep -i legion | tail -5 || true
	bash -c "./issue-warning.sh"

reloadmodule_disableplatformprofile:
	rmmod legion_laptop 2>/dev/null || true
	$(load_deps)
	insmod legion-laptop.ko enable_platformprofile=0 || { dmesg | tail -15; exit 1; }
	@dmesg | grep -i legion | tail -5 || true
	bash -c "./issue-warning.sh"

forcereloadmodule_disableplatformprofile:
	rmmod legion_laptop 2>/dev/null || true
	$(load_deps)
	insmod legion-laptop.ko force=1 enable_platformprofile=0 || { dmesg | tail -15; exit 1; }
	@dmesg | grep -i legion | tail -5 || true
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
