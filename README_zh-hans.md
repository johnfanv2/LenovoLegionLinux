<h1 align="left">
  <a href="https://github.com/johnfanv2/LenovoLegionLinux" target="_blank">
    <picture>
      <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/johnfanv2/LenovoLegionLinux/HEAD/doc/assets/legion_logo_dark.svg">
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/johnfanv2/LenovoLegionLinux/HEAD/doc/assets/legion_logo_light.svg">
      <img alt="LenovoLegionLinux" src="https://raw.githubusercontent.com/johnfanv2/LenovoLegionLinux/HEAD/doc/assets/legion_logo_dark.svg" height="50" style="max-width: 100%;">
    </picture>
  </a>
    <strong> 联想拯救者 Linux 支持 </strong>
</h1>

[![构建状态](https://github.com/johnfanv2/LenovoLegionLinux/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/johnfanv2/LenovoLegionLinux/actions/workflows/build.yml)
[![加入Discord](https://img.shields.io/discord/761178912230473768?label=拯救者系列Discord)](https://discord.com/invite/legionseries)
[![Reddit社区](https://img.shields.io/static/v1?label=Reddit&message=LenovoLegion&color=green)](https://www.reddit.com/r/LenovoLegion/)
[![更多Reddit](https://img.shields.io/static/v1?label=Reddit&message=linuxhardware&color=blueviolet)](https://www.reddit.com/r/linuxhardware/)
</br>
[![Ubuntu/Debian PPA](https://img.shields.io/badge/Ubuntu%2FDebian-Debian软件库-red)](https://tracker.debian.org/pkg/lenovolegionlinux)
[![Fedora Copr](https://img.shields.io/badge/Nobara%2FFedora-LenovoLegionLinux-blue)](https://copr.fedorainfracloud.org/coprs/mrduarte/LenovoLegionLinux/)
[![AUR软件包](https://img.shields.io/aur/version/lenovolegionlinux-git?label=AUR软件包)](https://aur.archlinux.org/packages/lenovolegionlinux-git)
[![AUR DKMS](https://img.shields.io/aur/version/lenovolegionlinux-dkms-git?label=AUR软件包(dkms版))](https://aur.archlinux.org/packages/lenovolegionlinux-dkms-git)
[![Gentoo GURU](https://img.shields.io/badge/Gentoo%20Overlay-GURU-blueviolet)](https://gitweb.gentoo.org/repo/proj/guru.git/)
[![实时Ebuild](https://img.shields.io/badge/实时Ebuild-sys--firmware%2Flenovolegionlinux-blueviolet)](https://gpo.zugaina.org/sys-firmware/lenovolegionlinux)
[![NixOS](https://img.shields.io/badge/NixOS软件包-lenovo--legion-9cf)](https://search.nixos.org/packages?channel=unstable&from=0&size=50&sort=relevance&type=packages&query=lenovo-legion)
</br>
[![Nobara](https://img.shields.io/badge/Nobara_Linux-内核已打补丁-green)](https://nobaraproject.org/)
[![PikaOS](https://img.shields.io/badge/PikaOS_Linux-内核已打补丁-green)](https://pika-os.com/)
---

#### 本README文件的其他语言版本：

* [English Version](README.md)

---

**本项目与联想(Lenovo)官方无任何关联**  

<!-- # 如果您拥有2022或2023款机型，请协助测试新功能[点击此处](https://github.com/johnfanv2/LenovoLegionLinux/issues/46)  

# 如果您的设备带有顶盖Y字logo灯或IO接口指示灯（所有Legion 7机型），请协助测试灯光控制[点击此处](https://github.com/johnfanv2/LenovoLegionLinux/issues/54) -->  

Lenovo Legion Linux（LLL）为联想拯救者系列笔记本提供了额外的Linux驱动和工具集，可作为Windows专属的"Lenovo Vantage"和"Legion Zone"控制软件的替代方案。  

通过逆向工程和反汇编ACPI固件、嵌入式控制器(EC)的固件与内存，本项目实现了以下功能控制：  
- 风扇曲线调节  
- 性能模式切换  
- 功耗限制调整  
- 快速充电管理  
- 及其他高级功能  

:star: **如果本项目对您有帮助或可能有潜在价值，请为仓库点赞（Star）**  

:star2: **我们的终极目标是将驱动整合进Linux内核主线，未来无需在系统更新后重新编译驱动**  

:boom: **您的点赞将向Linux社区证明该项目的价值，推动驱动进入官方内核的进程**  

## :rocket: 功能特性  

<p align="center">
    <img height="300" style="float: center;" src="doc/assets/fancurve_gui.jpg" alt="风扇曲线界面">
    <img height="300" style="float: center;" src="doc/assets/psensor.png" alt="传感器监控">
    <img height="300" style="float: center;" src="doc/assets/powermode.png" alt="性能模式">
</p>  
- [x] 占用内存和 CPU 极小，无遥测
- [x] 可完全通过脚本或命令行控制
- [x] 替代 Lenovo Vantage 的简单 GUI：风扇曲线、Fn 锁、Win 键、触控板电源、摄像头电源、电池养护、快速充电、始终开启 USB 充电输出、显示器超频、Y-Logo 灯光、IO 端口灯光、混合模式 (GSync)、CPU/GPU 超频：
  - 切换电池养护模式；接入电源时保持电池在 60%，延长电池寿命（https://bugs.kde.org/show_bug.cgi?id=441057）
  - 切换 Fn 锁；无需按 Fn 键即可使用 F1-F12 的特殊功能
  - 启用或禁用触控板
- [x] 设置最多 10 点的完整自定义风扇曲线：
  - 设置各温度节点对应的风扇转速（等级）变化点
  - 可同时用 CPU、GPU 和 IC 温度控制风扇
  - 每一级可设置风扇转速（RPM）
  - 支持 1600 RPM 以下的转速
  - 设置每一级风扇降速所需低于的最低温度
  - 分别设置风扇加速和减速的响应参数
  - 支持不同模式下的预设保存与加载
- [x] 锁定和解锁风扇控制器与风扇转速
- [x] 通过软件切换电源模式（静音、平衡、高性能）
  - 现在可在系统设置中通过软件切换
  - 也可通过 `Fn+Q` 切换
  - 根据桌面环境，可实现如在电池下自动切入静音模式，接电源时自动切入高性能模式（如 KDE 的节能设置）
  - 可根据电源配置文件自动切换不同风扇曲线（见：[ Lenovo Legion Linux 守护进程（legiond）](# Lenovo Legion Linux 守护进程（legiond）)）
- [x] 通过新增的传感器监控风扇转速和温度（CPU、GPU、IC）
- [x] 启用或禁用在长时间低温下自动切换为“迷你风扇曲线”

---

## :mega: 项目架构  
- **标准化驱动模块**：通过Linux标准接口（sysfs/debugfs/hwmon）实现  
- **全兼容设计**：  
  - 命令行操作（直接文件读写）  
  - 完美适配psensor等主流监控工具  
- **超越Windows原厂工具**：  
  - 彻底解决风扇"启停式噪音"问题  
  - 办公场景下实现持续低噪运行  

---

## :package: 可用软件包

- Debian/Ubuntu：
  - Debian 仓库（临时）：[地址](https://tracker.debian.org/pkg/lenovolegionlinux)
- Fedora/RHEL 系列发行版：
    - 官方 Fedora COPR：[地址](https://copr.fedorainfracloud.org/coprs/mrduarte/LenovoLegionLinux/)
- Arch 系列发行版：
    - [lenovolegionlinux-git](https://aur.archlinux.org/packages/lenovolegionlinux-git)
    - [lenovolegionlinux-dkms-git](https://aur.archlinux.org/packages/lenovolegionlinux-dkms-git)
- Gentoo 系列发行版：
    - [GURU Overlay](https://gitweb.gentoo.org/repo/proj/guru.git)
    - [ebuild](https://gpo.zugaina.org/sys-firmware/lenovolegionlinux)
- [NixOS](https://search.nixos.org/packages?channel=unstable&from=0&size=50&sort=relevance&type=packages&query=lenovo-legion)

[^1]: 每天格林威治时间午夜打包最新提交版本

## :pushpin: 已确认兼容的型号

# 如果你拥有2022或2023年的机型，请在[这里](https://github.com/johnfanv2/LenovoLegionLinux/issues/46)帮助测试新功能。

# 如果你的笔记本在A面（Y标志）或接口区（所有Legion 7）有灯，请在[这里](https://github.com/johnfanv2/LenovoLegionLinux/issues/54)帮助测试灯控功能。

**其他2020至2023年的联想拯救者机型大概率也能兼容。以下为已确认可用的具体型号。如果你的BIOS版本前缀相同，例如EFCN（如EFCN54WW），那很可能也能兼容。如果你想确认你的型号是否可用，或发现不可用，请提交issue。**

- 联想拯救者 5 15IMH05, 15IMH05H（BIOS EFCN54WW）：传感器、风扇曲线、电源配置
- 联想拯救者 5 15ACH6H（BIOS GKCN58WW 或 GKCN57WW），第六代：传感器、风扇曲线、电源配置
- 联想拯救者 R9000（R9000K2021H）（BIOS GKCN59WW）：传感器、风扇曲线、电源配置
- 联想拯救者 5 Pro 16ACH6H (82JQ)（BIOS GKCN58WW）x 2：传感器、风扇曲线、电源配置
- Legion 5 Pro 16ACH6H（AMD 5800H + Nvidia RTX 3070）：传感器、风扇曲线、电源配置
- 联想拯救者 5 15ARH05A（BIOS FSCN14WW），第五代：传感器、风扇曲线
- 联想拯救者 5 15ARH05H（BIOS FSCN14WW 或 FSCN26WW），第五代：传感器、风扇曲线、电源配置
- 联想拯救者 5 15ITH6H（BIOS H1CN49WW，Intel）：传感器、风扇曲线、电源配置
- 联想拯救者 5 15ARH7H（BIOS JUCN55WW），第七代：传感器、风扇曲线、电源配置
- 联想拯救者 5 15ACH6（BIOS HHCN31WW）：传感器、风扇曲线、电源配置
- 联想拯救者 S7 16ARHA7（BIOS KFCN32WW）：传感器、风扇曲线（无mini风扇曲线）、电源配置
- 联想拯救者 5 Pro 16ITH6（BIOS H1CN52WW（H1CN51WW的CPU温度有误））：传感器、风扇曲线、电源配置
- 联想拯救者 5 15ACH6A（BIOS G9CN30WW），全AMD版本：传感器、风扇曲线（含mini风扇曲线）、电源配置
- 联想拯救者 5 17ACH6（BIOS HHCN31WW）：传感器、风扇曲线、电源配置
- 联想拯救者 7i 16ITHG6（BIOS H1CN35WW）：传感器、风扇曲线、电源配置
- 联想拯救者 7 Pro 16ARX8H（BIOS LPCN47WW）：传感器、风扇曲线、电源配置

*注：未确认的功能大概率也能使用，只是暂无测试。*

目前，以下型号暂不支持风扇控制，但其他功能大概率可用：

- BIOS为HACN*的Legion机型，如S7-15ACH6：[相关Issue](https://github.com/johnfanv2/LenovoLegionLinux/issues/13)
- Legion Y530和Legion Y540：[相关Issue](https://github.com/johnfanv2/LenovoLegionLinux/issues/16)
- 大部分Legion第8代（2023年）

## :warning: 免责声明

- **本工具不提供任何担保，使用风险自负。**
- **本项目与联想公司无任何关联。**
- 这是一个小型业余项目，请耐心等待，并在寻求支持前仔细阅读本说明文档
- 如果你的联想拯救者笔记本暂不支持，且你愿意协助测试，请联系我
- 该工具仅支持Linux系统，可能无法在WSL下运行；如需Windows支持，请使用以下Windows工具：
  - [LenovoLegionToolkit](https://github.com/BartoszCichecki/LenovoLegionToolkit)
  - [LegionFanControl](https://www.legionfancontrol.com/)

## :bulb: 使用说明

请按如下步骤操作：

- **请先按安装说明进行安装**
- **然后进行测试**
- **如果测试通过，再进行永久安装**
- **创建你的自定义风扇曲线**

### 依赖要求

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
# 如需通过 DKMS 安装，请安装以下包
sudo pacman -S dkms openssl mokutil
```

*注意：请确认安装了正确的Header包。*

常见问题排查：

- 报错 `ERROR: Kernel configuration is invalid.`，只需重新安装内核头文件，例如在Debian：

```bash
sudo apt install --reinstall linux-headers-$(uname -r)
```

### 构建与测试说明

```bash
git clone https://github.com/johnfanv2/LenovoLegionLinux.git
cd LenovoLegionLinux/kernel_module
make
sudo make reloadmodule
```

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

### 永久安装说明

在成功编译和测试后（见上文），在 `LenovoLegionLinux/kernel_module` 目录下运行：

```bash
make
sudo make install
```

**每次内核更新后，你都需要再次编译和安装一次，如同其他外部内核模块一样。**
目标是将驱动合入主线Linux内核，这样将来无需再做这些操作。如果觉得本项目有用，欢迎star支持！

### 卸载说明

进入 `LenovoLegionLinux/kernel_module` 目录：

```bash
make
sudo make uninstall
```

### 使用 DKMS 安装

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

#### 安全启动（Secure boot）

如果你想让驱动程序在开启安全启动（Secure Boot）的情况下工作，请按照这里描述的步骤操作  
https://github.com/dell/dkms#secure-boot 或 https://wiki.archlinux.org/title/User:Krin/Secure_Boot,_full_disk_encryption,_and_TPM2_unlocking_install#Secure_boot。注意，这些步骤略显高级。对于初步测试，只需按照上面的步骤加载模块，或者关闭安全启动即可。

### 通过 DKMS 卸载

```
sudo dkms remove -m LenovoLegionLinux -v 1.0.0
reboot
```

### 永久性内核补丁

这只适用于那些自己编译内核的高级用户。  
每当达到稳定里程碑时，发布页面会自动生成补丁：[Releases](https://github.com/johnfanv2/LenovoLegionLinux/releases)

## :octocat: 初次使用测试

请注意：

- 请按给定顺序测试；在继续下一个之前请先尝试修复失败的测试。
- 这些测试是手动在终端中进行的，因为这是该工具的早期版本。
- 你可以复制并粘贴命令。在终端内使用 `Ctrl+Shift+V` 粘贴。

### 快速测试：模块是否正确加载

```bash
# 在 LenovoLegionLinux/kernel_module 目录下（非 DKMS 方式）
sudo make reloadmodule 

# 检查内核日志
sudo dmesg
```

预期结果：

- 你应该看到类似 `legion PNP0C09:00: legion_laptop loaded for this device` 的日志信息。`PNP0C09` 可能会被其他文本替换。

非预期结果：

- 执行 `make reloadmodule` 后出现 `insmod: ERROR: could not insert module legion-laptop.ko: Invalid module format`
- 日志中出现 `legion PNP0C09:00: legion_laptop not loaded for this device`。说明内核模块未能正确加载，请重新执行第一次测试。
- 出现 `insmod: ERROR: could not insert module legion-laptop.ko: Key was rejected by service`：因为你开启了安全启动，无法加载内核模块。请在 BIOS 里禁用安全启动，或用私钥签名内核模块。
- 如果看到如下内容，说明该驱动未针对你的笔记本型号测试过；如果你觉得应该兼容，请向维护者反馈。如果你仍想在你的型号上尝试，可以使用 `sudo make forcereloadmodule` 强制加载模块。

```text
[126675.495983] legion PNP0C09:00: Module not usable for this laptop because it is not in allowlist. Notify maintainer if you want to add your device or force load with param force.
[126675.495984] legion PNP0C09:00: legion_laptop not loaded for this device
[126675.496014] legion: probe of PNP0C09:00 failed with error -12
```

### 快速测试：读取当前硬件风扇曲线

```bash
# 读取当前风扇曲线及其他调试输出
sudo cat /sys/kernel/debug/legion/fancurve
```

预期输出：

- EC chip ID 应为 8227
- “fan curve points” 的 size 不能为 0
- 显示当前风扇曲线的表格内不能全为 0，实际数值可能会不同
- “fan curve current point id” 和 “EC Chip Version” 可能与示例不同

示例：

```text
EC Chip ID: 8227 
EC Chip Version: 2a4 
fan curve current point id: 0 
fan curve points size: 8 
Current fan curve in UEFI
u(speed_of_unit)|speed1[u]|speed2[u]|speed1[pwm]|speed2[pwm]|acceleration|deceleration|cpu_min_temp|cpu_max_temp|gpu_min_temp|gpu_max_temp|ic_min_temp|ic_max_temp
3        0       0       0       0       3       3       0       50      0       50      0       30
3        11      11      28      28      3       3       50      55      50      55      30      40
3        13      13      33      33      3       3       55      60      55      60      40      50
3        20      20      51      51      3       3       60      65      60      65      50      55
3        22      22      56      56      3       3       65      70      65      70      55      127
3        24      24      61      61      3       3       70      75      70      75      127     127
3        28      28      71      71      2       2       75      80      75      80      127     127
3        33      33      84      84      2       2       80      88      80      88      127     127
3        40      40      102     102     2       2       88      90      88      90      127     127
3        44      44      112     112     2       2       90      127     90      127     127     127

```

风扇曲线以表格形式展示，列说明如下：

```text
u(speed_of_unit): 风扇速度的单位（1-百分比, 2-PWM, 3-RPM）
speed1[u]: fan1 在该点的速度（rpm 除以 100）
speed2[u]: fan2 在该点的速度（rpm 除以 100）
speed1[pwm]: fan1 在该点的 pwm（0-255）
speed2[pwm]: fan2 在该点的 pwm（0-255）
acceleration: 加速时间（数值越大越慢）
deceleration: 减速时间（数值越大越慢）
cpu_min_temp: CPU 必须低于该温度才能离开此点
cpu_max_temp: CPU 高于此温度则跳到下一个点
gpu_min_temp: GPU 必须低于该温度才能离开此点
gpu_max_temp: GPU 高于此温度则跳到下一个点
ic_min_temp: IC 必须低于该温度才能离开此点
ic_max_temp: IC 高于此温度则跳到下一个点

所有温度单位为摄氏度。
127 为最大温度
```

**注意**：这只是调试输出。风扇曲线的配置仍然通过标准的 `hwmon` 接口进行。

异常情况：

- `/sys/kernel/debug/legion/fancurve: No such file or directory`：内核模块未正确加载
- `cat: /sys/kernel/debug/legion/fancurve: Permission denied`：你忘记加 sudo

### 快速测试：读取硬件传感器数值

- 显示传感器数值，并检查是否包含 “Fan 1”、 “Fan 2”、 “CPU Temperature”、 “GPU Temperature” 的相关行：

```bash
# 运行命令 sensors
sensors
```

- 显示传感器数值
- 增加 CPU 负载，并检查：
  - 显示的 CPU 温度是否升高
  - 显示的风扇转速是否升高
- 再次显示传感器数值
- 增加 GPU 负载，并检查 GPU 温度是否变化
  - 显示的 CPU 温度是否升高
  - 显示的风扇转速是否升高

预期输出：

- `sensors` 命令的输出应包含如下内容：

  ```text
  legion_hwmon-isa-0000
  Adapter: ISA adapter
  Fan 1:           1737 RPM
  Fan 2:           1921 RPM
  CPU Temperature:  +42.0°C  
  GPU Temperature:  +30.0°C  
  IC Temperature:   +41.0°C  
  ```
- 如果 GPU 处于深度休眠，其温度会显示为 0；可以运行一些 GPU 程序来测试
- 温度应为有效值：特别是不能为 0（除了 GPU，上述情况除外）
- 风扇转速应为有效值：风扇停止时为 0，否则应大于 1000 rpm
- 温度与风扇转速应根据负载变化而上升

异常输出：

- `Command 'sensors' not found`：请通过安装 `lm-sensors` 软件包获取 `sensors` 命令
- 没有 “Fan 1”、 “Fan 2” 等条目显示。说明内核模块未正确加载，请重新执行第一次测试。

---

### 快速测试：通过 hwmon 更改当前硬件风扇曲线

```bash
# 将风扇曲线第二、第三个点的风扇转速分别设置为 1500 rpm、1600 rpm、1700 rpm、1800 rpm。
# 获取 root 权限
sudo su
# 以 root 身份输入：
# 第2点，第1风扇（大约 1500 rpm 的 pwm 值）
echo 38 > /sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/hwmon*/pwm1_auto_point2_pwm
# 第2点，第2风扇（大约 1600 rpm 的 pwm 值）
echo 40 > /sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/hwmon*/pwm2_auto_point2_pwm
# 第3点，第1风扇（大约 1700 rpm 的 pwm 值）
echo 43 > /sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/hwmon*/pwm1_auto_point3_pwm
# 第3点，第2风扇（大约 1800 rpm 的 pwm 值）
echo 45 > /sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/hwmon*/pwm2_auto_point3_pwm

# 读取当前风扇曲线并检查更改是否生效
cat /sys/kernel/debug/legion/fancurve
```

预期结果：

- 如果你按下 Ctrl+Q（或某些设备的 FN+Q）更改电源模式，或等待时间过长，控制器可能会加载默认值；此时请重试
- 风扇曲线中的对应条目值应被设置为你输入的数值，其它值不相关（用 XXXX 表示）

```
u(speed_of_unit)|speed1[u]|speed2[u]|speed1[pwm]|speed2[pwm]|acceleration|deceleration|cpu_min_temp|cpu_max_temp|gpu_min_temp|gpu_max_temp|ic_min_temp|ic_max_temp
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             15        16        38          40          XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             17        18        43          45          XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX
XXXX             XXXX      XXXX      XXXX        XXXX        XXXX         XXXX         XXXX         XXXX         XXXX         XXXX         XXXX        XXXX

```

**如果你想重置风扇曲线，只需按 Ctrl+Q 或 Fn+Q 切换电源模式，或重启即可恢复。**

异常情况：

- `file not found`：请在 Github 提交 issue 报告你的问题
- 数值没有变化
- 读到的数值与预期不同

### 快速测试：设置自定义风扇曲线

使用提供的脚本设置自定义风扇曲线。参见下文“创建并设置你自己的风扇曲线”。

### 测试：结束

- 如果你对测试结果满意，可以永久安装内核模块（见上文）。
- 无论测试成功还是失败，请创建一个 GitHub Issue 进行反馈。
  - 请务必注明你的笔记本电脑型号
  - 如果出现错误，请附上命令的输出结果
- 你也可以为本仓库点个星

## :computer: 正常使用

**你必须永久安装内核模块（见上文），否则每次重启后都需要手动重新加载内核模块**

### 温度与风扇监控

温度和风扇转速可以在任何监控这些参数的图形化工具中显示，例如 psensor。你需要先安装它，然后运行：

```bash
psensor
```

<p align="center">
    <img height="450" style="float: center;" src="doc/assets/psensor.png" alt="psensor">
</p>

### 使用 Python GUI 更改和设置自定义风扇曲线

以 root 身份启动 GUI

```bash
# 在 LenovoLegionLinux 文件夹下运行
sudo python/legion_linux/legion_linux/legion_gui.py
```

<p align="center">
    <img height="450" style="float: center;" src="doc/assets/fancurve_gui.jpg" alt="fancurve">
</p>

- 点击 `Read from HW` 可以读取并显示保存在硬件中的当前风扇曲线。
- 你可以编辑风扇曲线的各项数值。只有点击 `Apply to HW` 后，修改才会写入硬件并生效。
- 点击 `Apply to HW` 可将当前显示的风扇曲线写入硬件并激活。
- 你可以将风扇曲线保存为预设或从预设加载。通过下拉菜单选择预设，然后点击 `Load from Preset` 或 `Save to preset`。
- 加载预设只会显示内容，必须点击 `Apply to HW` 才会激活到硬件。
- 预设以 yaml 文件的形式保存在 `/root/.config/legion_linux/`，你也可以手动编辑这些文件。
- 风扇曲线点的数量依据电源模式而定。未激活的点当前显示为 `0`。
- 锁定风扇控制器：启用后会冻结当前风扇转速和用于控制风扇的温度。

异常情况：

- 显示错误或所有值为 `0`：内核模块未加载或未安装（见上文）或不兼容（请按照上方手动测试）。
- 使用 `Write to HW` 写入硬件时某个值被拒绝：说明该值超出硬件允许范围。

### 使用 Python CLI 更改和设置自定义风扇曲线

你也可以通过 CLI 程序实现和 GUI 相同的功能，并可访问相同的预设。

```bash
# 在 LenovoLegionLinux 文件夹下运行
sudo python/legion_linux/legion_linux/legion_cli.py
```

```text
usage: legion_cli.py [-h] {fancurve-write-preset-to-hw,fancurve-write-hw-to-preset,fancurve-write-file-to-hw,fancurve-write-hw-to-file} ...

Legion CLI

options:
  -h, --help            显示帮助信息并退出

子命令:
  {fancurve-write-preset-to-hw,fancurve-write-hw-to-preset,fancurve-write-file-to-hw,fancurve-write-hw-to-file}
    fancurve-write-preset-to-hw
                        将预设中的风扇曲线写入硬件
    fancurve-write-hw-to-preset
                        将硬件中的风扇曲线写入预设
    fancurve-write-file-to-hw
                        将文件中的风扇曲线写入硬件
    fancurve-write-hw-to-file
                        将硬件中的风扇曲线写入文件
```

### 使用脚本创建并设置自定义风扇曲线

只需运行脚本即可设置风扇曲线。脚本位于 `LenovoLegionLinux` 文件夹中。

```bash
# 进入 LenovoLegionLinux 文件夹并运行脚本。如果成功完成，应该会输出 "Writing fancurve successful!"
sudo ./setmyfancurve.sh
# 检查新的风扇曲线
sudo cat /sys/kernel/debug/legion/fancurve
```

打开 `setmyfancurve.sh` 文件，编辑其中的数值以自定义你的风扇曲线。具体请参考文件中的说明。

异常输出：

- `bash: ./setmyfancurve.sh: Permission denied`：你需要先用 `chmod +x ./setmyfancurve` 让脚本具有可执行权限
- 脚本未以 "fancurve set" 结尾：可能 hwmon 路径发生了变化，请向项目反馈此问题

注意事项：

- **如果你想重置风扇曲线，只需按下 Ctrl+Q 或 Fn+Q 切换电源模式，或重启系统即可恢复默认。**
- 目前没有可用的 GUI。
- 目前，硬件可能会随机重置风扇曲线，或者在你更换电源模式、挂起、重启时重置。此时只需重新运行脚本即可。
- 你可以为不同的使用场景创建不同的脚本。只需复制脚本并调整相关数值即可。

---

### 通过软件更改电源模式

要使用此功能，必须永久安装内核模块（见上文）。或者，在重新加载内核模块后，重启电源守护进程（Ubuntu 下为 `systemctl restart power-profiles-daemon.service`）。

#### 使用 GUI 修改/控制

通过 GUI，可以在标有 `Power mode/platform profile` 的框中选择当前电源模式。

#### 使用小部件修改/控制

在 Ubuntu/Gnome 中，进入 `设置->电源->电源模式/节能选项` 或使用右上角的小程序进行切换。

<p align="center">
    <img height="450" style="float: center;" src="doc/assets/powermode.png" alt="psensor">
</p>

自动切换电源模式可以在发行版的设置中更改（如 Ubuntu）。

#### 使用 CLI 修改

```bash
# 列出所有配置文件（power-saver = 静音 = 蓝色）
powerprofilesctl list

#   performance:
#     Driver:     platform_profile
#     Degraded:   no

#   balanced:
#     Driver:     platform_profile

# * power-saver:
#     Driver:     platform_profile

# 设置某个配置，例如 power-saver=静音
powerprofilesctl set power-saver
# 或平衡
powerprofilesctl set balanced
# 或高性能
powerprofilesctl set performance
```

你也可以用更底层的方式直接访问：

```bash
# 查看当前配置
cat /sys/firmware/acpi/platform_profile

# 更改当前配置（需要ROOT权限）：可用模式有 quiet、balanced、performance、balanced-performance
# quiet = 节能
echo quiet > /sys/firmware/acpi/platform_profile
# 或平衡
echo balanced > /sys/firmware/acpi/platform_profile
# 或高性能
echo performance > /sys/firmware/acpi/platform_profile
# 或自定义模式 = balanced-performance（并非所有型号都支持）；LED 会变为粉色/紫色
echo balanced-performance > /sys/firmware/acpi/platform_profile
```

#### 自定义电源模式

如果你的机型支持自定义电源模式，可以：

- 进入自定义电源模式
- LED 会变为粉色/紫色
- 可自定义 CPU/GPU 的加速和 TGP 设置

你可以在 GUI 中选择 "Custom Mode" 进入自定义模式。或者，也可以用命令行切换：

```bash
echo balanced-performance > /sys/firmware/acpi/platform_profile
```

遗憾的是，目前 `power-profile-deamon` 或 `powerprofilesctl` 还不支持该模式。

### 启用或禁用迷你风扇曲线

如果笔记本长时间保持低温，会启用“迷你风扇曲线”，这是一种只包含少量节点的特殊风扇曲线，通常会让风扇持续转动。你可以选择启用或禁用它。如果你希望始终使用自己配置的风扇曲线，请将其禁用。并非所有机型都支持迷你风扇曲线（如果不支持，运行 `cat /sys/kernel/debug/legion/fancurve` 时会看到相关错误）。

在 GUI 中，通过勾选或取消 `Minifancurve if cold` 选项并点击 `Apply to HW` 按钮来启用或禁用迷你风扇曲线。

---

### Lenovo Legion Linux 守护进程（legiond）

LLL 守护进程支持 Systemd 和 OpenRC（实验性）。  
如果你是手动安装 LLL（不是通过包管理器），可能需要在 extra 文件夹里运行 [systemd_install.sh](extra/systemd_install.sh)。

该守护进程可以根据电源模式和是否插电，自动切换 GUI 中设定的风扇曲线配置文件。  
可用的配置文件如下：

- quiet-battery - 电池供电下安静模式风扇配置
- balance-battery - 电池供电下平衡模式风扇配置
- balanced-performance-battery - 电池供电下自定义模式风扇配置
- quiet-ac - 充电器供电下安静模式风扇配置
- balance-ac - 充电器供电下平衡模式风扇配置
- balanced-performance-ac - 充电器供电下自定义模式风扇配置
- performance-ac - 充电器供电下高性能模式风扇配置

示例配置文件在 [这里](extra/service/profiles)，也可以通过 GUI 便捷设置：

1. 先设置你想要的 `Fan Curve`
2. 在 `Fancurve Preset` 选择上述某个配置文件，然后点击 `Save to Preset`（会要求输入密码）
3. 依次设置好所有配置文件
4. 进入 `Automation` 标签，启用 `Lenovo Legion Laptop Support Daemon Enable` 选项

此 systemd 服务还支持通过编辑 `/etc/legion_linux/legiond.ini`（即 [legiond.ini](extra/service/legiond.ini)）激活以下附加功能：

- cpu_control - 启用 AMD 下的 RyzenADJ 或 Intel 的降压功能，根据电源模式自定义 CPU 设置
  - bat_bp - 电池自定义模式下 CPU 设置
  - ac_bp - 充电器自定义模式下 CPU 设置
  - bat_q - 电池安静模式下 CPU 设置
  - ac_q - 充电器安静模式下 CPU 设置
  - bat_b - 电池平衡模式下 CPU 设置
  - ac_b - 充电器平衡模式下 CPU 设置
  - ac_p - 充电器高性能模式下 CPU 设置
- gpu_control:
  - nvidia - 使用 `nvidia-smi -pl` 命令调整 NVIDIA GPU 的 TDP（仅支持驱动 525 及以下）
  - radeon - 使用 `rocm-smi --setpoweroverdrive` 命令调整 Radeon GPU 的 TDP

    - tdp_bat_bp - 电池自定义模式下 GPU TDP
    - tdp_ac_bp - 充电器自定义模式下 GPU TDP
    - tdp_bat_q - 电池安静模式下 GPU TDP
    - tdp_ac_q - 充电器安静模式下 GPU TDP
    - tdp_bat_b - 电池平衡模式下 GPU TDP
    - tdp_ac_b - 充电器平衡模式下 GPU TDP
    - tdp_ac_p - 充电器高性能模式下 GPU TDP
  - 注意：.env 文件中的默认值来自 RTX 3070

注意：`legiond.service` 依赖于 `acpid.service`，启用 `legiond.service` 时会自动启动 `acpid.service`。  
如果你的 CPU 调优经常被重置为默认值，请启用 `legiond-cpuset.timer` 来覆盖它。

详细见 [README.org](extra/service/legiond/README.org)

---

### 锁定与解锁风扇控制器和风扇转速

你可以锁定当前风扇转速。锁定后，风扇转速将保持不变，不会再随温度变化。如果你想在游戏时保持高转速，可以使用此功能，但不建议一直保持锁定。如果风扇控制器被 Windows 工具等意外锁定，你也可以解锁。风扇控制器被锁定时，温度传感器数据也不会更新。

在 GUI 中，勾选 `Lock fan controller` 并点击 `Apply to HW` 即可锁定风扇控制器。

---

### 设置风扇为最大转速

风扇可以设置为最大转速（极致散热/清灰模式），此时温度不会影响转速。请勿长时间开启此模式，否则可能加速风扇损耗。

在 GUI 中，勾选 `Set speed to maximum fan speed` 并点击 `Apply to HW` 即可。

注意：目前并非所有机型都支持此功能。

---

### 设置电池养护模式以延长电池寿命（接入电源时）

可以开启电池养护模式。开启后，插电时电池将不会持续充电，而是保持电量在 50% 左右，据说可延长电池寿命。

在 GUI 中，勾选 `Battery conservation` 即可开启（更改会立即生效）。

---

### 切换 Fn 锁，使 F1-F12 键可直接调用特殊功能

你可以锁定 Fn 键，方法是同时按下 Fn+Esc（部分型号 Esc 键灯会同步点亮/熄灭）。开启后，F1-F12 键无需 Fn 也能直接调用如调节音量等特殊功能。

在 GUI 中，勾选或取消 `Fn Lock` 即可（更改会立即生效）。

---

### 启用/禁用触控板

你可以通过 Fn+F10（或类似组合）开启或关闭触控板。

在 GUI 中，勾选或取消 `Touch Pad Enabled` 即可（更改会立即生效）。

### 键盘背光

- 4 区 RGB 背光：请使用 https://github.com/4JX/L5P-Keyboard-RGB
- 白色背光的开/关或开/中/高三档：本软件支持，也可以通过所有 Linux 下的 LED 控制程序进行控制

## 已知问题

由于硬件固件的限制，部分问题无法修复：

- 风扇曲线的点数无法更改（性能模式下为 10 点，其它模式为 9 点），但你可以通过将温度限制设置为 127 来实际禁用某些点，在写入 `auto_points_size` 时已经采用了这种方式。

## :clap: 鸣谢

### 本项目基础

感谢以下 Windows 工具的开发者，他们的工作为 Linux 支持奠定了基础：

* [SmokelessCPU](https://github.com/SmokelessCPUv2)，负责对嵌入式控制器固件的逆向工程，并发现了与嵌入式控制器通信的直接 IO 控制方法。
* [FanFella](https://github.com/SmokelessCPUv2)，找到了锁定或解锁风扇控制器的地址
* [Bartosz Cichecki](https://github.com/BartoszCichecki)，开发了 [LenovoLegionToolkit](https://github.com/BartoszCichecki/LenovoLegionToolkit)，这是一款适用于新款 Legion 型号的 Windows 工具，通过 ACPI/WMI 方法控制笔记本。本 README 也大量借鉴了该项目。
* [0x1F9F1](https://github.com/0x1F9F1)，负责对嵌入式控制器固件中的风扇曲线进行逆向工程，并开发了 Windows 工具 [LegionFanControl](https://github.com/0x1F9F1/LegionFanControl)
* [ViRb3](https://github.com/ViRb3)，开发了 [Lenovo Controller](https://github.com/ViRb3/LenovoController)，该项目为 [LenovoLegionToolkit] 提供了基础
* [Luke Cama](https://www.legionfancontrol.com/)，开发了闭源工具 [LegionFanControl](https://www.legionfancontrol.com/)，该工具通过直接与嵌入式控制器交互，支持旧款笔记本风扇控制
* David Woodhouse，开发了 ideapad Linux 驱动 [ideapad-laptop](https://github.com/torvalds/linux/blob/0ec5a38bf8499f403f81cb81a0e3a60887d1993c/drivers/platform/x86/ideapad-laptop.c)，为本 Linux 驱动带来了极大启发

### Lenovo Legion Linux的贡献者

感谢以下用户为 Linux 支持做出的贡献：

* [normaneye](https://github.com/normaneye)，修复了 GUI 中的 GPU 温度显示问题
* [Petingoso](https://github.com/Petingoso)，修复了脚本无需 sudo 即可运行的问题
* [XenHat](https://github.com/XenHat)，修正了 README 文档

如果你的笔记本支持或者不支持本项目，请也告知我们。

### 基于 Lenovo Legion Linux 的工具

#### Plasma Vantage
PlasmaVantage 是 KDE 的一个 Plasma 小部件，是 Lenovo Legion Linux 内核模块的替代 GUI。可在 [KDE 商店](https://store.kde.org/p/2150610/)获取，源码见 [这里](https://gitlab.com/Scias/plasmavantage)。

## :interrobang: 常见问题解答

### 新增的温度传感器有哪些？

这些是由嵌入式控制器测量和使用的温度，只对风扇控制器有实际意义。它们由新的内核模块提供，其他情况下无法获取，因为这些数据是直接从嵌入式控制器读取的。

### 新增的风扇转速传感器有哪些？

这些传感器会报告风扇转速（单位为 rpm，转/分）。它们同样由新的内核模块提供，其他情况下无法获取，因为这些数据也是从嵌入式控制器读取的。

### 控制风扇转速使用了哪些温度？

会使用 CPU、GPU 和 “IC” 的温度。这些（通常）是额外的传感器，与未使用内核模块时系统报告的温度不同。尤其是 “IC” 温度的阈值可能设置得很低，会导致风扇几乎一直转。

### 为什么我的 CPU 和 GPU 温度很低但风扇仍然在转？

请参考上文，尤其是 “IC” 温度传感器的影响。

### 风扇转速会根据功耗变化吗？

据我所知，并没有这个情况。目前观察到的风扇控制只和温度有关。

### 为什么我的风扇不加速、从不停止或速度一直不变（使用过其他工具后）？

如果风扇速度一直比较恒定，可能是风扇控制器被锁定（通常称为锁定风扇转速）。你可以在 GUI（见上文）中锁定/解锁风扇控制器。一般不建议锁定。进行 BIOS/UEFI 更新通常也会解锁，但请谨慎操作并建议做好 BIOS 备份。

如果风扇在高负载下始终没有加速，可能是风扇控制器被锁定（如上）。同时请检查 CPU（或 GPU）在负载下报告的温度是否确实升高。只有 “CPU Temperature”、“GPU Temperature” 和 “IC Temperature” 这三个温度会被用于风扇控制，这些温度是硬件风扇控制器内部实际用到的。

如果风扇从不停止，可能是你设置了很低的 CPU、GPU 或 IC 的最高温度阈值。许多机型即使在安静模式下也会有较低的温度阈值，导致风扇一直不会停止。你可以适当提高最低档位的温度阈值。

### 空闲时风扇很吵。

请参考上面相关说明。

### 浏览网页等轻量工作时风扇就启动了。

即使在浏览网页时，CPU 也可能会有短时间的负载，导致温度短暂升高从而风扇启动。你可以：

- 调整风扇曲线，特别是提高温度上限、增加加速时间
- 禁用 CPU 的加速模式（boost mode）
- 也可参考上面其它建议

### 报告的温度没有变化或看起来不正确。

请参考上面相关说明。

### 高负载下风扇转速还是不够快。

请参考上面相关说明。

### BIOS 更新后某些功能（如风扇控制）失效怎么办？

可能是 BIOS 更新过程中出现了问题。可以降级回旧版本测试，然后再重新升级，并再次检查当前版本下的功能是否正常。

### 如何升级 BIOS 或重置嵌入式控制器以修复问题？

最简单的方法是先降级到较旧版本，然后再升级回当前版本，并在旧版本下测试功能。  
你也可以尝试如下方式重置嵌入式控制器：

- 关闭笔记本，拔掉所有连接（充电器、USB 等）
- 按住电源键 60 秒不放；即使设备开机也要继续按住
- 60 秒后松开电源键
- 短按电源键开机

---

### 安静、平衡、高性能模式分别做了什么？

你可以通过 Fn+Q 切换模式，这会在固件中更改模式，并改变指示灯颜色，即使没有驱动支持（即无此内核模块）。

**在未安装 Lenovo Legion Linux 时切换电源模式：**

- 指示灯颜色变化
- 嵌入式控制器中的风扇曲线变化
- 可能还有其他纯硬件配置会改变，但目前未发现
- ~~据我所知，CPU 的省电或性能设置不会随之改变，这部分由内核或 cpupower 等工具控制~~
- 实际分析 ACPI 固件（存储于硬件中）后发现，某些电源选项（如 STAPM 限制）会通过 ACPI 调用更改 CPU/GPU 设置。可以通过 Fn+Q 切换电源模式并用 `ryzenadj` 检查 AMD CPU 的功率限制来观察。~~但在 Linux 下尚未观察到对 NVIDIA GPU 功率限制的更改，可能说明 ACPI 与 GPU 驱动集成存在问题~~。驱动 535+ 版本下，NVIDIA GPU 在电池供电时会调整功率限制（如 RTX 3070 在安静模式为 40w，平衡模式为 50w），插电时高性能模式会将功率限制设置为最大，但在高负载任务下性能或自定义模式会允许更高的功率。如果高性能模式下 GPU 功率上限卡在 80W 而非 Windows 下的 115W/130W，你可能受到了此 bug 的影响：[NVIDIA/open-gpu-kernel-modules#483](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/483)。
- 未安装 Lenovo Legion Linux 时，内核或系统工具不会知晓你切换了电源模式。

**安装 Lenovo Legion Linux 后切换电源模式：**

- 包含上述所有变化
- 此外，Lenovo Legion Linux 驱动会将电源模式信息传递给内核和如 Power Profiles daemon 等服务；这些服务可根据配置进一步调整 CPU/GPU 性能。

**在 Windows 下也类似**：切换电源模式会通知系统或如 Vantage 之类的工具，进而调整电源计划。

---

### 玩游戏时应该用平衡模式还是高性能模式？

两者在实际性能（FPS）上的差别很小。想追求极致性能就用高性能模式，日常推荐用平衡模式。

---

### 有一个风扇一直满速运转怎么办？

首先检查风扇曲线是否设置正确，确保不是配置错误。再检查用于风扇控制的温度（见 ["新增温度"](#what-are-the-new-fan-speed-sensors)）在空闲时是否过低。如果只有一个风扇满速，另一个能正常按曲线控制，建议[重置 BIOS 和 EC 控制器](#how-to-do-a-bios-upgrade-or-reset-the-embedded-controller-to-fix-a-problem)。

---

### BIOS 里的“高级散热优化”是什么？

你可以更改硬件中预设的风扇曲线和最小风扇转速：

- `off`：足够冷时关闭风扇
- `level 1`：最小风扇转速等级 1
- `level 2`：最小风扇转速等级 2
- `level 3`：最小风扇转速等级 3

参考：https://forums.lenovo.com/t5/Gaming-Laptops/Legion-7-Bios-What-is-advanced-thermal-optimization/m-p/5079357

---

### 我不用 GNOME，如何获得切换电源模式的漂亮小部件？

你可以直接用 Fn+Q 切换电源模式。

如果你用 KDE，可以在“电池与亮度”图标处切换。

如果不需要 GUI，可以[使用命令行](#modify-with-cli)。

其它桌面环境：
本驱动会将电源模式切换功能暴露给如 `power-profiles-daemon` 等工具。

建议先在终端测试（见 ["Powermode -> Modify with CLI"](#modify-with-cli)），如可用，再安装 `power-profiles-daemon`。

GNOME 的图形小程序会用 `power-profiles-daemon` 以软件方式切换电源模式，这是 GNOME 的标准功能，并未由本工具提供。

对于 KDE，有图形工具 `powerdevil`，其内部同样利用 `power-profiles-daemon`。

### 几乎都能用，但某些温度传感器/风扇控制节点或风扇转速无效，怎么办？

首先，尝试[重置嵌入式控制器](#how-to-do-a-bios-upgrade-or-reset-the-embedded-controller-to-fix-a-problem)或进行 BIOS 升级/降级来重置所有设置。

---

### 内核升级后无法使用怎么办？

方案一：重新编译/安装内核模块，参见：[永久安装说明](#permanent-install-instruction)。  
方案二：使用 DKMS 实现每次内核更新后自动安装，参见：[使用 DKMS 安装](#installing-via-dkms)。

---

### 即使在 Ubuntu 里关闭了，屏幕在一段时间不用后还是会变暗，如何解决？（GNOME）

```bash
gsettings set org.gnome.settings-daemon.plugins.power idle-brightness 100
```

参考：https://old.reddit.com/r/linuxquestions/comments/utle2w/ubuntu_2204_is_there_a_way_to_disable_screen/

---

### 如何在不用 dGPU 时彻底关闭它，并只用 iGPU 实现省电？

以下为在 Ubuntu（X11 环境）下的一种配置方法。这样默认所有程序运行在 iGPU 上，除非你另行指定。
- 检查 BIOS 是否开启了混合模式（Hybrid Mode）。
- 检查当前桌面环境是否为 X11 而非 Wayland：
```bash
# 应该输出 "x11"
echo $XDG_SESSION_TYPE
```
- 安装 `prime` 并选择“按需”模式，可能需要重启：
```bash
sudo prime-select on-demand
```
- 用 `nvidia-smi` 检查 dGPU 是否有进程在运行：
```bash
sudo nvidia-smi
```
  注意输出中 `0   N/A  N/A  ***  G   /usr/lib/xorg/Xorg   4MiB` 这种进程是正常的。另外，运行 `nvidia-smi` 本身会短暂唤醒 GPU。
- 允许进入 `d3cold` 模式：
```bash
# 注意：根据 GPU 设备路径，二选一
echo 1 > /sys/devices/pci0000\:00/0000\:00\:01.1/d3cold_allowed 
echo 1 > /sys/devices/pci0000\:00/0000\:00\:01.0/d3cold_allowed 
```
- 检查 GPU Runtime 的 D3 状态是否启用：
```bash
sudo cat /proc/driver/nvidia/gpus/0000:01:00.0/power
```
- 检查 GPU 当前状态：
```bash
# 注意：根据你的 GPU 设备路径，二选一，输出应为 "D3cold"
cat /sys/devices/pci0000\:00/0000\:00\:01.0/power_state
cat /sys/devices/pci0000\:00/0000\:00\:01.1/power_state 
```
- 运行 `nvidia-smi`，GPU 会被唤醒一段时间。再次检查 `power_state`，应先变为 `D0`，稍等后会回到 `D3cold`。与 `nvidia-smi` 不同，`cat /sys/devices/pci0000\:00/0000\:00\:01.1/power_state` 不会唤醒 GPU。

```bash
sudo cat /proc/driver/nvidia/gpus/0000:01:00.0/power
```



## :question: 未解答的问题

- 第三个温度传感器究竟是什么？目前称为 IC 温度（IC Temperature）。
- “静音模式（quiet mode）”适合玩游戏吗？

## :information_desk_person: 开发者概览

本软件包含两部分：

- `kernel_module` 文件夹下的内核模块：
  - 通过写入内存访问嵌入式控制器（EC）
  - 创建新的“文件”：如 `/sys/kernel/debug/legion/fancurve`、 `/sys/module/legion_laptop/drivers/platform\:legion/PNP0C09\:00/powermode`、 `/sys/class/hwmon/X/temp1_input`、 `/sys/class/hwmon/X/pwmY_auto_pointZ_pwm` 等，用户可以通过这些文件读取温度传感器、控制风扇曲线、切换电源模式等。

- `python` 文件夹下的 Python 包：
  - `legion.py`：用于从 Python 修改风扇曲线及其他设置的模块；封装了对上述内核模块及 `ideapad_laptop` 等模块提供的“文件”的读写；所有来自 `legion_gui.py` 和 `legion_cli.py` 的设置更改都通过本模块完成。
  - `legion_gui.py`：一个基于 `legion.py` 的图形界面（GUI）程序，用于更改设置。
  - `legion_cli.py`：一个基于 `legion.py` 的命令行（CLI）程序，用于更改设置。

## 法律声明

本项目中对任何联想产品、服务、流程或其它信息的引用，以及对联想商标的使用，并不构成或暗示联想对本项目的认可、赞助或推荐。

在本网站及相关工具和库中使用 Lenovo®、Lenovo Legion™、Yoga®、IdeaPad® 或其他商标，仅用于为用户提供可识别的标识，以便用户能够确认这些工具适用于联想笔记本电脑。