# Credits

## Basis of this work

Thank you for your work on Windows tools that were the basis of the Linux support:

* [SmokelessCPU](https://github.com/SmokelessCPUv2), for reverse engineering the embedded controller firmware
  and finding the direct IO control method to communicate with the embedded controller
* [FanFella](https://github.com/SmokelessCPUv2), for finding the address to lock or unlock the fan controller
* [Bartosz Cichecki](https://github.com/BartoszCichecki), for creating [LenovoLegionToolkit](https://github.com/BartoszCichecki/LenovoLegionToolkit), a Windows tool for newer Legion models that controls the Laptop with ACPI/WMI methods. Even this README is heavily inspired on it.
* [0x1F9F1](https://github.com/0x1F9F1), for reverse engineering the fan curve in the embedded controller firmware
  and creating the Windows tool [LegionFanControl](https://github.com/0x1F9F1/LegionFanControl)
* [ViRb3](https://github.com/ViRb3), for creating [Lenovo Controller](https://github.com/ViRb3/LenovoController), which was used as a base
  for [LenovoLegionToolkit]
* [Luke Cama](https://www.legionfancontrol.com/), for his closed-source tool [LegionFanControl](https://www.legionfancontrol.com/) that controls older laptops by directly interacting with the embedded controller
* David Woodhouse, for his work on the ideapad Linux driver [ideapad-laptop](https://github.com/torvalds/linux/blob/0ec5a38bf8499f403f81cb81a0e3a60887d1993c/drivers/platform/x86/ideapad-laptop.c), which was a heavy inspiration for this Linux driver

## Contributors to Lenovo Legion Laptop Support

Thank you for your contribution for the Linux support:

* [normaneye](https://github.com/normaneye), fixing GPU temperature bug in GUI
* [Petingoso](https://github.com/Petingoso), fix script to run withou sudo
* [XenHat](https://github.com/XenHat), fix README
* [Hishammm0](https://github.com/Hishammm0), Legion Pro 5 16IRX8 (KWCN) fan levels, kernel 7.x ACPI probe fix, clang build support

Also please tell me if it works or does not work on your laptop.

## Tools that are based on LenovoLegionLinux
### PlasmaVantage
PlasmaVantage is a Plasma Widget for KDE. It is an alternative GUI for the LenovoLegionLinux kernel module. It is available in the [KDE store](https://store.kde.org/p/2150610/) or with source [here](https://gitlab.com/Scias/plasmavantage).

### CinnamonVantage
CinnamonVantage is a Cinnamon Applet for Cinnamon. It is an alternative GUI for the LenovoLegionLinux kernel module. It is available in the [Mint store](https://cinnamon-spices.linuxmint.com/applets/view/395) or with source [here](https://github.com/linuxmint/cinnamon-spices-applets/tree/master/cinnamonvantage@garlayntoji).
