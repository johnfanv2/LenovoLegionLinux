# 安装

请按如下步骤操作：

- **请先按安装说明进行安装**
- **然后进行测试**
- **如果测试通过，再进行永久安装**
- **创建你的自定义风扇曲线**

## 依赖要求

你需要安装下列依赖以便下载与编译。如果某个依赖包名称出错，请在你的发行版中查找对应的替代包名并安装。

**Ubuntu/Debian/Pop!_OS/Mint/elementary OS/Zorin**

```bash
sudo apt-get update
sudo apt-get install -y make gcc linux-headers-$(uname -r) build-essential git lm-sensors wget python3-pyqt6 python3-yaml python3-venv python3-pip python3-argcomplete python3-darkdetect
# 如需通过 DKMS 安装，请安装以下包
sudo apt-get install dkms openssl mokutil
```

**RHEL/CentOS/RockyLinux/Fedora/AlmaLinux**

```bash
sudo dnf install -y kernel-headers kernel-devel dmidecode lm_sensors python3-PyQt6 python3-yaml python3-pip python3-argcomplete python3-darkdetect
sudo dnf groupinstall "Development Tools"
sudo dnf group install "C Development Tools and Libraries"
# 如需通过 DKMS 安装，请安装以下包
sudo dnf install dkms openssl mokutil
```

你也可以使用 `yum` 替代 `dnf`，并先执行 `sudo yum update`。某些发行版可能不需要安装 "C Development Tools and Libraries"。

**openSUSE**

```bash
sudo zypper install make gcc kernel-devel kernel-default-devel git libopenssl-devel sensors dmidecode python3-qt5 python3-pip python3-PyYAML python3-argcomplete python3-darkdetect
# 如需通过 DKMS 安装，请安装以下包
sudo zypper install dkms openssl mokutil
```

*注意：请确认安装了正确的Header包。*

**Arch/Manjaro/EndeavourOS**

```bash
sudo pacman -S linux-headers base-devel lm_sensors git dmidecode python-pyqt6 python-yaml python-argcomplete python-darkdetect
# 仅用于 clang 编译的内核（例如 CachyOS）；Makefile 会自动以 LLVM=1 构建
sudo pacman -S clang llvm lld
# 如需通过 DKMS 安装，请安装以下包
sudo pacman -S dkms openssl mokutil
```

*注意：请确认安装了正确的Header包。*

常见问题排查：

- 报错 `ERROR: Kernel configuration is invalid.`，只需重新安装内核头文件，例如在Debian：

```bash
sudo apt install --reinstall linux-headers-$(uname -r)
```

## 构建与测试说明

```bash
git clone https://github.com/johnfanv2/LenovoLegionLinux.git
cd LenovoLegionLinux/kernel_module
make
sudo make reloadmodule
```

*注意：* 在使用 clang 编译的内核上（`CONFIG_CC_IS_CLANG=y`，例如 CachyOS），Makefile 会自动检测并在内核构建中传入 `LLVM=1`（`make`、`make install` 与 DKMS 均适用）；请先安装 `clang`、`llvm` 和 `lld`。

**更多详细说明、问题和测试请见下方的 `首次使用测试` 部分，请务必先进行这些测试再进行永久安装。**

预期结果：

- `make` 命令完成且未出现 `Error` 报错信息

异常结果：

- `make` 命令中断报错
- 出现类似 `/lib/modules/XXXXXXXX/build: No such file or directory` 的报错，这说明当前内核的 linux-headers 未正确安装。请使用 `uname -r` 查看你当前内核，并为该内核版本安装对应的 linux-headers。此时 `/lib/modules/XXXXXXXX/` 目录下应有你的内核版本（如 `5.19.0-28-generic` 或 `6.2.9-arch1-1`）。如果刚刚升级过内核，重启后再试，或参考 https://bbs.archlinux.org/viewtopic.php?id=135931, https://forum.manjaro.org/t/missing-build-directory-in-5-15-16-1-manjaro-headers/101793。

```text
make[1]: *** /lib/modules/6.2.9-arch1-1/build: No such file or directory.  Stop.
make[1]: Leaving directory '/home/user/LenovoLegionLinux/kernel_module'
make: *** [Makefile:13: all] Error 2
```

## 永久安装说明

在成功编译和测试后（见[初次使用测试](initial-testing.md)），在 `LenovoLegionLinux/kernel_module` 目录下运行：

```bash
make
sudo make install
```

**每次内核更新后，你都需要再次编译和安装一次，如同其他外部内核模块一样。**
目标是将驱动合入主线Linux内核，这样将来无需再做这些操作。如果觉得本项目有用，欢迎star支持！

## 卸载说明

进入 `LenovoLegionLinux/kernel_module` 目录：

```bash
make
sudo make uninstall
```

## 使用 DKMS 安装

> DKMS 是一个工具，可在每次内核更新后自动重编译和安装驱动，无需手动操作。

首先需安装好 DKMS 相关依赖，见前文依赖部分。

```
sudo mkdir -p /usr/src/LenovoLegionLinux-1.0.0
sudo cp ./kernel_module/* /usr/src/LenovoLegionLinux-1.0.0 -r
sudo dkms add -m LenovoLegionLinux -v 1.0.0
sudo dkms build -m LenovoLegionLinux -v 1.0.0
```

也可以通过makefile快捷安装：

```
cd kernel_module
sudo make dkms # 需以root权限运行
```

### 安全启动（Secure boot）

如果你想让驱动程序在开启安全启动（Secure Boot）的情况下工作，请按照这里描述的步骤操作  
https://github.com/dell/dkms#secure-boot 或 https://wiki.archlinux.org/title/User:Krin/Secure_Boot,_full_disk_encryption,_and_TPM2_unlocking_install#Secure_boot。注意，这些步骤略显高级。对于初步测试，只需按照上面的步骤加载模块，或者关闭安全启动即可。

## 通过 DKMS 卸载

```
sudo dkms remove -m LenovoLegionLinux -v 1.0.0
reboot
```

## 永久性内核补丁

这只适用于那些自己编译内核的高级用户。  
每当达到稳定里程碑时，发布页面会自动生成补丁：[Releases](https://github.com/johnfanv2/LenovoLegionLinux/releases)
