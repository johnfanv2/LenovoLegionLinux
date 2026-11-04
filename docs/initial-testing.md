# Initial Usage Testing

Please note:

- Please test in the given order; try to fix a failed text before going to the next.
- These tests are manual and run in the terminal
- You can copy-and-paste the commands. Paste with `Ctrl+Shift+V` inside the terminal.

## Quick Test: Module is properly loaded

```bash
# After you have run from folder LenovoLegionLinux/kernel_module (for non DKMS)
sudo make reloadmodule 

# Check the kernel log
sudo dmesg
```

Expected result:

- You should see a line like the following like `legion PNP0C09:00: legion_laptop loaded for this device`. `PNP0C09` might be replaced by other text.

Unexpected result:

- `insmod: ERROR: could not insert module legion-laptop.ko: Invalid module format` after running `make reloadmodule`
- `legion PNP0C09:00: legion_laptop not loaded for this device`. The kernel module was not loaded properly. Redo first test.
- `insmod: ERROR: could not insert module legion-laptop.ko: Key was rejected by service`: because you enable secure boot, you cannot load kernel modules.   Disable secure boot (in BIOS) or sign the kernel module with a private key.
- if you see the following, the driver was not tested for your laptop model; please [create an issue](https://github.com/johnfanv2/LenovoLegionLinux/issues/new/choose) with the maintainer if you think it should be compatible. If you want to try it anyhow with your model use `sudo make forcereloadmodule`

```text
[126675.495983] legion PNP0C09:00: Module not usable for this laptop because it is not in allowlist. Notify maintainer if you want to add your device or force load with param force.
[126675.495984] legion PNP0C09:00: legion_laptop not loaded for this device
[126675.496014] legion: probe of PNP0C09:00 failed with error -12
```

## Quick Test: Reading Current Fancurve from Hardware

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

The fan curve is displayed as a table with the following columns:

```text
u(speed_of_unit): unit for the speed (1-Percentage, 2-PWM, 3-RPM/100, 4-Percentage rounded to nearest, 5-Level index 0-10 into the firmware fan table)
speed1[u]: speed of fan1 at this point, in the unit given by u
speed2[u]: speed of fan2 at this point, in the unit given by u
speed1[pwm]: speed in pwm (0-255) for fan1 at this point
speed2[pwm]: speed in pwm (0-255) for fan2 at this point
acceleration: acceleration time (higher = slower)
deceleration: deceleration time (higher = slower)
cpu_min_temp: CPU temperature must go below this before leaving this point
cpu_max_temp: if CPU temperature is above this value, go to next point 
gpu_min_temp: GPU temp must go below this before leaving this level
gpu_max_temp: if GPU temperature is above this value, go to next point 
ic_min_temp: IC temp must go below this before leaving this level
ic_max_temp: if IC temperature above this value, go to next point

All temperatures are in degree Celsius.
127 is the max temperature
```

**Note**: This is just a debug output. The fan curve is configured as usual using the standard `hwmon` interface.

Unexpected:

- `/sys/kernel/debug/legion/fancurve: No such file or directory`: Kernel module was not loaded properly
- `cat: /sys/kernel/debug/legion/fancurve: Permission denied` you have forgot sudo

## Quick Test: Read Sensor Values from Hardware

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

## Quick Test: Change Current Fan Curve from Hardware with hwmon

```bash
# Change the RPM of fans at the second and third point of the fan curve to 1500 rpm, 1600 rpm, 1700 rpm, 1800 rpm.
# Get root
sudo su
# As root enter
# The hwmon directory is named after the platform device, which is PNP0C09:00 before kernel 7.0 and "legion" on 7.0+;
# find it via the hwmon name instead:
H=$(grep -l legion_hwmon /sys/class/hwmon/hwmon*/name | xargs dirname)
# Check the unit first: on "level" models the values below are NOT rpm-like
# (pwm 38 -> level 1); if it says "percent" but the default table looks like
# 1 2 3 4 5 6 7 8 ..., stop and open an issue instead of writing.
cat /sys/devices/platform/legion/fancurve_speed_unit 2>/dev/null || cat /sys/bus/platform/devices/PNP0C09:00/fancurve_speed_unit
# 2. point, 1. fan (around 1500 rpm in pwm)
echo 38 > $H/pwm1_auto_point2_pwm
# 2. point, 2.fan (around 1600 rpm in pwm)
echo 40 > $H/pwm2_auto_point2_pwm
# 3. point, 1. fan (around 1700 rpm in pwm)
echo 43 > $H/pwm1_auto_point3_pwm
# 3. point, 2.fan (around 1800 rpm in pwm)
echo 45 > $H/pwm2_auto_point3_pwm


# Read the current fancurve and check if changes were made
cat /sys/kernel/debug/legion/fancurve
```

Expected:

- the controller might have loaded default values if you pressed Ctrl+Q(or FN+Q on certain devices) to change the power mode or waited too long; then try again
- on some firmware (e.g. Legion Slim 7 16IRH8, BIOS M0CN, [#637](https://github.com/johnfanv2/LenovoLegionLinux/issues/637)) a written table is **not** reset by a reboot or a power mode change; only an EC reset (unplug everything and hold the power button for 60 s) restores the firmware defaults
- The entries in the fan curve are set to their values. The other values are not relevant (marked with XXXX)
- On Legion Zone v3 firmware (e.g. Legion Pro 5 16IRX8, BIOS KWCN) the table holds fan levels 0-10 (`u` = 5): a written pwm is rounded to the nearest level (write 0, 26, 51, ... 255) and reads back as `level * 255 / 10` (0, 25, 51, 76, 102, 127, 153, 178, 204, 229, 255), points 9 and 10 need at least pwm 64 and 115, and a write below a point's minimum returns `Operation not supported`. The Python tools (`legion_cli`, `legion_gui` and the `legiond` presets) convert RPM values to the nearest firmware level on these models (for example 4400 rpm → level 9) and raise a 0 rpm point to the point's minimum level, so existing presets keep working. The per-level RPM ladders used for this are read at runtime from the driver's `fan1_level_rpm_table`/`fan2_level_rpm_table` platform attributes (filled from the firmware's `LENOVO_FAN_TABLE_DATA` WMI block), not hardcoded. `fan_maxspeed` (Fan Method ids 3/4) is not exposed on these models (KWCN, Q7CN, RLCN, QNCN): the firmware implements neither method, so the attribute cannot work (on KWCN it read a meaningless 0); `fan_control.sh` skips the attribute when it is absent

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

**If you want to reset your fan curve, just toggle with Ctrl+Q or Fn+Q the power mode or restart and everything is gone.**

Unexpected:

- `file not found`: please report your problem as a Github Issue
- the values have not changed
- there are different values

## Quick Test: Set your custom fan curve

Set a custom fan curve with the provided script. See [Creating and Setting your own Fan Curve with Script](usage.md#creating-and-setting-your-own-fan-curve-with-script).

## Test: Finish

- If you are satisfied with the test results, then you can install the kernel module permanently (see [Permanent Install Instruction](installation.md#permanent-install-instruction)).
- Create a GitHub Issue and report if the test work or fail.
  - Please include exact laptop model
  - If errors occurred, include output of commands.
- You also might to want to star this repository
