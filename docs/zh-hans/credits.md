# 鸣谢

## 本项目基础

感谢以下 Windows 工具的开发者，他们的工作为 Linux 支持奠定了基础：

* [SmokelessCPU](https://github.com/SmokelessCPUv2)，负责对嵌入式控制器固件的逆向工程，并发现了与嵌入式控制器通信的直接 IO 控制方法。
* [FanFella](https://github.com/SmokelessCPUv2)，找到了锁定或解锁风扇控制器的地址
* [Bartosz Cichecki](https://github.com/BartoszCichecki)，开发了 [LenovoLegionToolkit](https://github.com/BartoszCichecki/LenovoLegionToolkit)，这是一款适用于新款 Legion 型号的 Windows 工具，通过 ACPI/WMI 方法控制笔记本。本 README 也大量借鉴了该项目。
* [0x1F9F1](https://github.com/0x1F9F1)，负责对嵌入式控制器固件中的风扇曲线进行逆向工程，并开发了 Windows 工具 [LegionFanControl](https://github.com/0x1F9F1/LegionFanControl)
* [ViRb3](https://github.com/ViRb3)，开发了 [Lenovo Controller](https://github.com/ViRb3/LenovoController)，该项目为 [LenovoLegionToolkit] 提供了基础
* [Luke Cama](https://www.legionfancontrol.com/)，开发了闭源工具 [LegionFanControl](https://www.legionfancontrol.com/)，该工具通过直接与嵌入式控制器交互，支持旧款笔记本风扇控制
* David Woodhouse，开发了 ideapad Linux 驱动 [ideapad-laptop](https://github.com/torvalds/linux/blob/0ec5a38bf8499f403f81cb81a0e3a60887d1993c/drivers/platform/x86/ideapad-laptop.c)，为本 Linux 驱动带来了极大启发

## Lenovo Legion Linux的贡献者

感谢以下用户为 Linux 支持做出的贡献：

* [normaneye](https://github.com/normaneye)，修复了 GUI 中的 GPU 温度显示问题
* [Petingoso](https://github.com/Petingoso)，修复了脚本无需 sudo 即可运行的问题
* [XenHat](https://github.com/XenHat)，修正了 README 文档
* [Hishammm0](https://github.com/Hishammm0)，Legion Pro 5 16IRX8（KWCN）风扇等级、内核 7.x ACPI 探测修复、clang 构建支持

如果你的笔记本支持或者不支持本项目，请也告知我们。

## 基于 Lenovo Legion Linux 的工具

### Plasma Vantage
PlasmaVantage 是 KDE 的一个 Plasma 小部件，是 Lenovo Legion Linux 内核模块的替代 GUI。可在 [KDE 商店](https://store.kde.org/p/2150610/)获取，源码见 [这里](https://gitlab.com/Scias/plasmavantage)。

### CinnamonVantage
CinnamonVantage 是 Cinnamon 桌面的一个小程序（Applet），是 LenovoLegionLinux 内核模块的替代 GUI。可在 [Mint 商店](https://cinnamon-spices.linuxmint.com/applets/view/395)获取，源码见 [这里](https://github.com/linuxmint/cinnamon-spices-applets/tree/master/cinnamonvantage@garlayntoji)。
