<img height="50" align="left" src="assets/headerlogo.png" alt="HeaderLogo">

# LenovoLegionLinux

[![Build](https://github.com/johnfanv2/LenovoLegionLinux/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/johnfanv2/LenovoLegionLinux/actions/workflows/build.yml)
[![Join Discord](https://img.shields.io/discord/761178912230473768?label=Legion%20Series%20Discord)](https://discord.com/invite/legionseries)
[![Check Reddit](https://img.shields.io/static/v1?label=Reddit&message=LenovoLegion&color=green)](https://www.reddit.com/r/LenovoLegion/)
[![More Reddit](https://img.shields.io/static/v1?label=Reddit&message=linuxhardware&color=blueviolet)](https://www.reddit.com/r/linuxhardware/)

---

LenovoLegionLinux (LLL) brings additional drivers and tools for Lenovo Legion series laptops to Linux. It
is the alternative to Lenovo Vantage or Legion Zone (both Windows only).

It allows to control a few features like fan curve and power mode.

:star: **Please star this repository if this is useful or might be useful in the future.**

:star2: **My goal is to merge the driver into the main Linux kernel so it comes automatically with Linux and no recompilation is required after a Linux update**

:boom: **Starring shows that this is useful to me and the Linux community so hopefully a merge into the Kernel is possible.**

## :mega: Overview
- it comes with a driver (kernel module) that implements the Linux standard interfaces (sysfs, debugfs, hwmon) 
- using standard Linux interfaces makes it is compatible with the command line/file interface or standard GUI tools like psensor
- compared to vendor tools for Windows, it even allows to set the fan curve. This allows to keep the fans
    slowly and quietly running instead of constantly switching between fans off and loud fans. Perfect for quiet office work. :office:

## :pushpin: Confirmed Compatible Models
Other Lenovo Legion models from 2020 to 2023 probably also work. The following were confirmed
- Lenovo Legion 5 15IMH05 (BIOS EFCN54WW): sensors and fan curve
- Lenovo Legion 5 15ACH6H (BIOS GKCN58WW), Gen 6: sensors and fan curve
- Lenovo Legion 5 15ARH05A (BIOS FSCN14WW), Gen 5: sensors and fan curve

## :warning: Disclaimer

- **The tool comes with no warranty. Use at your own risk.**
- **currently comes without a UI; commandline and script only**
- this is a small hobby project; please be patient and read through this readme carefully before you ask for support
- if your Lenovo Legion laptop is not supported and you are ready to perform some tests please notify me
- this is a Linux only tool and will probably also not run in WSL; for Windows use one of the availabe Windows tools
    - LenovoLegionToolkit
    - LegionFanControl


## :bulb: Instructions
Please do the following: 
- **follow installation instructions**
- **then make the test**
- **if tests are succesful, install permantely**
- **create your fan curve**

### Requirements
You will need to install the following to download and build it. If there is an error of any package, find the alternative name in your distro install them.

**Ubuntu/Debian**
```bash
sudo apt-get update
sudo apt-get install make gcc linux-headers-$(uname -r) build-essential git lm-sensors dmidecode
```

**RHEL/CentOS**
```bash
sudo yum update
sudo yum install kernel-headers kernel-devel lm-sensors dmidecode
sudo yum groupinstall "Development Tools"
sudo yum group install "C Development Tools and Libraries"
```

**Fedora**
```bash
sudo dnf install kernel-headers kernel-devel lm-sensors dmidecode
sudo dnf groupinstall "Development Tools"
sudo dnf group install "C Development Tools and Libraries"
```

**openSUSE**
```bash
sudo zypper install make gcc kernel-devel kernel-default-devel git libopenssl-devel lm-sensors dmidecode
```
*Note:* Check for the correct Header package.


**Arch/Manjaro**
```bash
sudo pacman -S linux-headers base-devel lm-sensors git dmidecode 
```
*Note:* Check for the correct Header package.

Troubleshooting: 
- Got error `ERROR: Kernel configuration is invalid.`. Just reinstall kernel headers, e.g. in Debian:
```bash
sudo apt install --reinstall linux-headers-$(uname -r)
```

### Build and Test Instruction
```bash
git clone https://github.com/johnfanv2/LenovoLegionLinux.git
cd LenovoLegionLinux/kernel_module
make
sudo make reloadmodule
```
For tests see `Initial Usage Testing` below. Do them first.

### Permanent Install Instruction
After successfully building and testing (see below), run from the folder `LenovoLegionLinux/kernel_module`
```bash
make
sudo make install
```

### Uninstall Instruction
Go to the folder `LenovoLegionLinux/kernel_module`
```bash
make
sudo make uninstall
```

## :octocat: Initial Usage Testing
Please note:
- Please test in the given order; try to fix a failed text before going to the next. 
- These tests are manual and in the terminal because this is an early version of this tool
- You can copy-and-paste the commands. Paste with `Ctrl+Shift+V` inside the terminal.

### Quick Test: Module is properly loaded
```bash
# After you have run from folder LenovoLegionLinux/kernel_module
sudo make reloadmodule

# Check the kernel log
sudo dmesg
```
Expected result: 
- You should see a line like the following like `legion PNP0C09:00: legion_laptop loaded for this device`. `PNP0C09` might be replaced by other text.

Unexpected result:
- `insmod: ERROR: could not insert module legion-laptop.ko: Invalid module format` after running `make reloadmodule`
- `legion PNP0C09:00: legion_laptop not loaded for this device`. The kernel module was not loaded properly. Redo first test.



### Quick Test: Reading Current Fancurve from Hardware
```bash
# Read the current fancurve and other debug output
sudo cat /sys/kernel/debug/legion/fancurve
```

Expected output:
- EC Chip ID should be 8227
- "fan curve points" size must NOT be 0
- the table that shows the current fan curve must NOT be only zeros, the actual values might change
- "fan curve current point id" and "EC Chip Version" might differ from the example
    
Example:
```text
EC Chip ID: 8227 
EC Chip Version: 2a4 
fan curve current point id: 0 
fan curve points size: 8 
Current fan curve in UEFI
rpm1|rpm2|acceleration|deceleration|cpu_min_temp|cpu_max_temp|gpu_min_temp|gpu_max_temp|ic_min_temp|ic_max_temp
0 0 2 2 0 48 0 59 0 41
1700 1900 2 2 45 54 55 59 39 44
1900 2000 2 2 51 58 55 59 42 50
2200 2100 2 2 55 62 55 59 46 127
2300 2400 2 2 59 71 55 59 127 127
2600 2700 2 2 68 76 55 64 127 127
2900 3000 2 2 72 81 60 68 127 127
3500 3500 2 2 78 127 65 127 127 127
```

The fan curve is displayed as a table with the following columns:
```text
rpm1: speed in rpm for fan1 at this point
rpm2: speed in rpm for fan1 at this point
acceleration: accelleration time (higher = slower)
deceleration: deceleration time (higher = slower)
cpu_min_temp: CPU temperatue must go below this before leaving this point
cpu_max_temp: if CPU temperature is above this value, go to next point 
gpu_min_temp: GPU temp must go below this before leaving this level
gpu_max_temp: if GPU temperature is above this value, go to next point 
ic_min_temp: IC temp must go below this before leaving this level
ic_max_temp: if IC temperature above this value, go to next point 

All temperatures are in degree Celsius.
```
**Note**: This is just a debug output. The fan curve is configured as usual using the standard `hwmon` interface.


Unexpected:
- `/sys/kernel/debug/legion/fancurve: No such file or directory`: Kernel module was not loaded properly
- `cat: /sys/kernel/debug/legion/fancurve: Permission denied` you have forgot sudo

### Quick Test: Read Sensor Values from Hardware
- display sensor values and check that it contains lines with "Fan 1", "Fan 2", "CPU Temperature", "GPU Temperature":
```bash
# Run the command sensors
sensors
```
- display sensor values
- increase the CPU load and check if 
    - displayed CPU temperature increases
    - displayed fan speed increases 
- display sensor values
- increase the GPU load and check if GPU temperature changes
    - displayed CPU temperature increases
    - displayed fan speed increases 

Expected output:
- Output of `sensors` contains something like
    ```text
    legion_hwmon-isa-0000
    Adapter: ISA adapter
    Fan 1:           1737 RPM
    Fan 2:           1921 RPM
    CPU Temperature:  +42.0°C  
    GPU Temperature:  +30.0°C  
    IC Temperature:   +41.0°C  
    ```
- if GPU is in deep sleep, its reported temperature is 0; run something on the GPU to test it
- temperatures are valid: in particular not 0 (except GPU see above)
- fan speeds are valid: if fan is off it is 0, otherwise greater than 1000 rpm
- temperatures and fan speeds increase as expected

Unexpected output:
- `Command 'sensors' not found`: Install `sensors` from the package `lm-sensors`     
- no entries for "Fan 1", "Fan 2" etc. are shown. The kernel module was not loaded properly. Redo first test.
    

### Quick Test: Change Current Fancurve from Hardware with hwmon
```bash
# Change the RPM of fans at the second and third point of the fan curve to 1500 rpm, 1600 rpm, 1700 rpm, 1800 rpm.
# Get root
sudo su
# As root enter
# 2. point, 1. fan
echo 1500 > /sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/hwmon*/pwm1_auto_point2_pwm
# 2. point, 2.fan
echo 1600 > /sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/hwmon*/pwm2_auto_point2_pwm
# 3. point, 1. fan
echo 1700 > /sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/hwmon*/pwm1_auto_point3_pwm
# 3. point, 2.fan
echo 1800 > /sys/module/legion_laptop/drivers/platform:legion/PNP0C09:00/hwmon/hwmon*/pwm2_auto_point3_pwm


# Read the current fancurve and check if changes were made
cat /sys/kernel/debug/legion/fancurve
```
Expected: 
- the controller might have loaded default values if you pressed Ctr+Q(or FN+Q on certain devices) to change the powermode or waited too long; then try again
- The entries in the fan curve are set to their values. The other values are not relevant (marked with XXXX)
```
rpm1|rpm2|acceleration|deceleration|cpu_min_temp|cpu_max_temp|gpu_min_temp|gpu_max_temp|ic_min_temp|ic_max_temp
XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX
1500 1600 XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX
1700 1800 XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX
XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX
XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX
XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX
XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX
XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX XXXX
```

**If you want to reset your fan curve, just toggle with Ctrl+Q the powermode or restart and everything is gone.**

Unexpected: 
- `file not found`: please report your problem as a Github Issue
- the values have not changed
- there are different values


### Quick Test: Set your custom fan curve
Set a custom fan curve with the provided script. See `Creating and Setting your own Fan Curve` below.


### Test: Finish
- If you are satisfied with the test results, then you can install the kernel module permanently (see above).
- Create a GitHub Issue and report if the test work or fail. 
    - Please include exact laptop model
    - If errors occurred, include output of commands.
- You also might to want to start this repository

## :computer: Normal Usage
**you have to install the kernel module permanently (see above), otherwise you must reload it manually after each restart**

### Temperature and Fan Monitoring
The temperatures and fan speeds should be displayed in any graphical tool that monitors them, e.g. psensor. You have to install it first before running:
```bash
psensor
```
<p align="center">
    <img height="450" style="float: center;" src="assets/psensor.png" alt="psensor">
</p>
    
### Creating and Setting your own Fan Curve
Just run the script to set the fan curve. It is in the folder `LenovoLegionLinux`.
```bash
# Go to folder LenovoLegionLinux and run it. It should output "Writing fancurve successful!" if it finishes successful
sudo ./setmyfancurve.sh
# And check new fan curve
sudo cat /sys/kernel/debug/legion/fancurve
```
Open the file `setmyfancurve.sh` and edit it to adapt the values in the script to create your own fan curve. Follow the description in the file.

Unexpected output:
- `bash: ./setmyfancurve.sh: Permission denied`: You have to make the script executable with `chmod +x ./setmyfancurve` first
- script does not end with "fancurve set": maybe path to hwmon changed; Please report this

Note: 
- **If you want to reset your fan curve, just toggle with Ctrl+Q the powermode or restart and everything is gone.**
- Currently, there is no GUI available. 
- Currently, the hardware resets the fan curve randomly or if you change powermode, suspend, or restart. Just run the script again. 
- You might want to create different scripts for different usages. Just copy it and adapt the values.


## :clap: Credits

### Basis of this work
Thank you for your work on Windows tools that were the basis of the Linux support:
* [SmokelessCPU](https://github.com/SmokelessCPUv2), for reverse engineering the embedded controller firmware
    and finding the direct IO control of the embedded controller
* [Bartosz Cichecki](https://github.com/BartoszCichecki), for creating [LenovoLegionToolkit](https://github.com/BartoszCichecki/LenovoLegionToolkit), a Windows tool for newer Legion models that controls the Laptop with ACPI/WMI methods. Even this README is heavily inspired on it.
* [0x1F9F1](https://github.com/0x1F9F1), for reverse engineering the fan curve in the embedded controller firmware 
    and creating the Windows tool [LegionFanControl](https://github.com/0x1F9F1/LegionFanControl)
* [ViRb3](https://github.com/ViRb3), for creating [Lenovo Controller](https://github.com/ViRb3/LenovoController), which was used as a base 
    for [LenovoLegionToolkit]
* [Luke Cama](https://www.legionfancontrol.com/), for his closed-source tool [LegionFanControl](https://www.legionfancontrol.com/) that controls older laptops with direclty with the embedded controller 
* David Woodhouse, for his work on the ideapad Linux driver [ideapad-laptop](https://github.com/torvalds/linux/blob/0ec5a38bf8499f403f81cb81a0e3a60887d1993c/drivers/platform/x86/ideapad-laptop.c), which was a heavy inspiration for this Linux driver

### Contributors to Lenovo Legion Laptop Support
:( Nothing here yet. Please tell me if it works on your laptop.
