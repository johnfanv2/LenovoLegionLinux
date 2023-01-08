SHELL := /bin/bash

container:
	make -C $(KSRC) M=$(PWD) clean
