# Installation

Please do the following:

- **follow installation instructions**
- **then make the test**
- **if tests are successful, install permanently**
- **create your fan curve**

## Requirements

You will need to install the following to download and build it. If there is an error of any package, find the alternative name in your distribution and install them.

**Ubuntu/Debian/Pop!_OS/Mint/elementary OS/Zorin**

```bash
sudo apt-get update
sudo apt-get install -y make gcc linux-headers-$(uname -r) build-essential git lm-sensors wget python3-pyqt6 python3-yaml python3-venv python3-pip python3-argcomplete python3-darkdetect
# Install the following for installation with DKMS
sudo apt-get install dkms openssl mokutil
```

**RHEL/CentOS/RockyLinux/Fedora/AlmaLinux**

```bash
sudo dnf install -y kernel-headers kernel-devel dmidecode lm_sensors python3-PyQt6 python3-yaml python3-pip python3-argcomplete python3-darkdetect
sudo dnf groupinstall "Development Tools"
sudo dnf group install "C Development Tools and Libraries"
# Install the following for installation with DKMS
sudo dnf install dkms openssl mokutil
```

Alternatively, you might use `yum` instead of `dnf` and start with `sudo yum update`. Installing "C Development Tools and Libraries" might not be needed depending of your distribution.

**openSUSE**

```bash
sudo zypper install make gcc kernel-devel kernel-default-devel git libopenssl-devel sensors dmidecode python3-qt5 python3-pip python3-PyYAML python3-argcomplete python3-darkdetect
# Install the following for installation with DKMS
sudo zypper install dkms openssl mokutil
```

*Note:* Check for the correct Header package.

**Arch/Manjaro/EndeavourOS**

```bash
sudo pacman -S linux-headers base-devel lm_sensors git dmidecode python-pyqt6 python-yaml python-argcomplete python-darkdetect
# Only for kernels built with clang (e.g. CachyOS); the Makefile then builds with LLVM=1 by itself
sudo pacman -S clang llvm lld
# Install the following for installation with DKMS
sudo pacman -S dkms openssl mokutil
```

*Note:* Check for the correct Header package.

Troubleshooting:

- Got error `ERROR: Kernel configuration is invalid.`. Just reinstall kernel headers, e.g. in Debian:

```bash
sudo apt install --reinstall linux-headers-$(uname -r)
```

## Build and Test Instruction

```bash
git clone https://github.com/johnfanv2/LenovoLegionLinux.git
cd LenovoLegionLinux/kernel_module
make
sudo make reloadmodule
```

*Note:* on kernels built with clang (`CONFIG_CC_IS_CLANG=y`, e.g. CachyOS) the Makefile detects this and passes `LLVM=1` to the kernel build by itself, for `make`, `make install` and DKMS alike; install `clang`, `llvm` and `lld` first.

**For further instructions, problems, and tests see [Initial Usage Testing](initial-testing.md). Do them first before a permanent installation.**

Expected result:

- `make` finishes without displaying `Error`

Unexpected result:

- `make` aborts with an error
- an error of kind `/lib/modules/XXXXXXXX/build: No such file or directory` like the following below. This means that the linux-headers are not installed properly for the current kernel. Please check your currrent kernel with `uname -r` and install linux-headers for it. Then there will be a directory `/lib/modules/XXXXXXXX/` where XXXXXX is the current kernel version, e.g. `5.19.0-28-generic` or `6.2.9-arch1-1`. If you have just updated your packages a restart might help or see https://bbs.archlinux.org/viewtopic.php?id=135931, https://forum.manjaro.org/t/missing-build-directory-in-5-15-16-1-manjaro-headers/101793.

```text
make[1]: *** /lib/modules/6.2.9-arch1-1/build: No such file or directory.  Stop.
make[1]: Leaving directory '/home/user/LenovoLegionLinux/kernel_module'
make: *** [Makefile:13: all] Error 2
```

## Permanent Install Instruction

After successfully building and testing (see [Initial Usage Testing](initial-testing.md)), run from the folder `LenovoLegionLinux/kernel_module`

```bash
make
sudo make install
```

**You must recompile and reinstall it again with above commands after each kernel update, as usual for external kernel modules.**
I want to get it merged into the mainline Linux kernel, so this is not needed anymore. So please star this repository :)

## Uninstall Instruction

Go to the folder `LenovoLegionLinux/kernel_module`

```bash
make
sudo make uninstall
```

## Installing via DKMS

> DKMS is a utility that eliminates the need to manually rebuild and reinstall the driver after every kernel update. DKMS will do the reinstallation automatically.

You must first install the package to with DKMS. See Requirements section.

```
sudo mkdir -p /usr/src/LenovoLegionLinux-1.0.0
sudo cp ./kernel_module/* /usr/src/LenovoLegionLinux-1.0.0 -r
sudo dkms add -m LenovoLegionLinux -v 1.0.0
sudo dkms build -m LenovoLegionLinux -v 1.0.0
```

Or via makefile

```
cd kernel_module
sudo make dkms # Don't forget to run as root
```

### Secure boot

If you want the driver to work with secure boot, then follow the steps described here
https://github.com/dell/dkms#secure-boot or here https://wiki.archlinux.org/title/User:Krin/Secure_Boot,_full_disk_encryption,_and_TPM2_unlocking_install#Secure_boot. Note that this is a little more advanced. For initial testing, just load the module as described in the steps above or disable secure boot.

## Uninstalling via DKMS

```
sudo dkms remove -m LenovoLegionLinux -v 1.0.0
reboot
```

## Permanently Patching the Kernel

This is only useful for advanced users that build there own kernel.
A automatically generated patch is provided on the release page whenver a stable milestone has been reached: [Releases](https://github.com/johnfanv2/LenovoLegionLinux/releases)
