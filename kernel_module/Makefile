SHELL := /bin/bash
KERNELVERSION  ?= $(shell uname -r)
KSRC := /lib/modules/$(KERNELVERSION)/build

#install dir for kernel drivers
INSTALLDIR := /lib/modules/$(KERNELVERSION)/kernel/drivers/platform/x86
MODDESTDIR := /lib/modules/$(KERNELVERSION)/kernel/drivers/platform/x86

obj-m += legion-laptop.o

all:
	$(MAKE) -C $(KSRC) M=$(shell pwd) modules

allWarn:
	$(MAKE) -C $(KSRC) M=$(shell pwd) KCFLAGS=-W modules

clean:
	make -C $(KSRC) M=$(shell pwd) clean

install: all
	@rm -f $(INSTALLDIR)/legion-laptop.ko
	@mkdir -p $(MODDESTDIR)
	@install -p -D -m 644 *.ko $(INSTALLDIR)
	@depmod -a $(KVER)
	@echo "Installion finished."

uninstall:
	@rm -f $(INSTALLDIR)/legion-laptop.ko
	@depmod -a
	@echo "Uninstall finished."

reloadmodule:
	rmmod legion-laptop.ko || true
	insmod legion-laptop.ko
	dmesg

forcereloadmodule:
	rmmod legion-laptop.ko || true
	insmod legion-laptop.ko force=1
	dmesg
