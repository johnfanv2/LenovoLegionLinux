# Frequently Asked Questions

## What are the new temperatures?

These are the temperatures measured and used by the embedded controller. Only they are relevant for the fan controller.
They are provided by the new kernel module and otherwise not accessible because they are read from the embedded controller.

## What are the new fan speed sensors?

They report the fan speed in revolutions per minute (rpm). They are provided by the new kernel module and otherwise not accessible because they are read from the embedded controller.

## What temperatures are used for controlling the fan speed?

The CPU, GPU, and "IC" temperature is used. These are (usually) additional sensors that are different from the temperature sensors that are reported when you do not use the kernel model. In particular, the "IC" temperature limit might be set to a low value which results in almost-always running fans.

## My CPU and GPU temperatures are low but the fan is still running?

See above. In particular, the  "IC" temperature sensor.

## Is the fan speed controlled by power consumption?

I have no reason to believe that. As far as I know and observed, only the temperatures are used.

## My fans do not spin up, never stop, or never change speed (after using other tools)?

If they always have roughly constant speed, maybe you have locked the fan controller, often called locking fan speed.
You can unlock/lock the fan speed controller in the GUI (see [Usage](usage.md)). I would recommend not locking them. Doing
a BIOS/UEFI update usually also unlocks it. But beware and consider making a BIOS (re)-update.

If the fans never spin up fast even under hight load, the fan controller might be locked (above). Additionally,
also check that the reported temperatures for CPU (or GPU) really increase under load. Only, the temperatures
"CPU Temperature", "GPU Temperature", and "IC Temperature" are used for fan control. These, are used internally
by the fan controller in hardware.

If otherwise the fans never stop, you might have set a very low upper temperature limit for CPU, GPU or IC. Many
models also come with a low temperature limit even on quiet mode, so fans never really turn off. You can just increase the temperature
limits for the lowest level.

## The fans are loud when idle.

See above.

## The fans turn on when doing light work like browsing.

Even when browsing there might be small bursts of work for the CPU. So it gets hot for a short time and the fans turn on. You can:

- Change the fan curve, in particular increase temperature limit and increase acceleration time
- Disable CPU boost mode
- Also see above

## The reported temperatures do not change or seem wrong.

See above.

## Even under high load, the fans are not going fast enough.

See above.

## After a BIOS update something, e.g. the fan controls, does not work anymore?

Maybe there was a problem during the BIOS update. Downgrade to an older version again. Then test it with the old version. Then do the BIOS upgrade again and check with the version.

## How to do a BIOS upgrade or reset the embedded controller to fix a problem?

The easiest way is to downgrade to a older version and then upgrade to the current version again. Also test it with the old version.
You can also just try reset the embedded controller by:

- Shutdown laptop, unplug everything (charger, USB, ...)
- Press AND hold power button for 60 seconds; keep holding even if it turns on
- After 60 seconds, release power button
- Press power button shortly to turn laptop on

## What does quiet, balanced, or performance mode do?

You can switch the mode by pressing Fn+Q and it will change the mode in the firmware and the color of the LED, even without any driver support (= without this kernel module).

Changing power mode without Lenovo Legion Linux is purely implemented in hardware:

- The color of LED changes.
- Fan curve in embedded controller changes.
- Other purely hardware configs might also change, but I have not observed one.
- ~~As far as I know, power saving or performance of CPU does not change, as this is controlled by kernel or tools like cpupower~~
- An analysis of the ACPI firmware, which is "stored in hardware", shows that some power options, e.g. the STAPM limit, of the CPU and GPU are changed via ACPI calls. This can be observed by changing power mode with Fn+Q and checking CPU power limits, e.g. with `ryzenadj` for AMD CPUs. ~~However, no changes to the GPU power limits are observed on NVIDIA GPUs, which might indicate that the integration of ACPI and GPU driver is faulty on Linux~~ On driver 535+, GPU power limits for nvidia changes on battery power (40w on quiet and 50w on balanced for RTX 3070), on power adapter, the power limit are allways set to max on peformance (reported by `nvidia-smi`), but more power is allowed to the GPU on performance or custom mode in demanding GPU tasks. If the GPU power limit on performance mode is stuck on 80W compared to 115W/130W on Windows, you're affected by this bug: [NVIDIA/open-gpu-kernel-modules#483](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/483).
- Without Lenovo Legion Linux, the kernel or other system tools will not know that you have changed the power mode.

Changing power mode **with** Lenovo Legion Linux:

- It changes all of the above.
- Additionally the driver in Lenovo Legion Linux makes this information available to the kernel and other services like the Power Profiles daemon; Those can, if configured, change the performance of the CPU or GPU.

On Windows it is similar: Changing the power mode is reported to the system or tools like Vantage which change the power plan.

## Should I use balanced mode or performance for gaming?

The difference in usable performance (FPS) is minimal. Use performance mode to get the utmost highest performance, otherwise use the balanced mode.

## One fan runs at full speed all the time. What should I do?

First check that the fan curve is set properly and this is **not** a misconfiguration. Then check if the temperatures used for fan control (see: ["new temperatures"](#what-are-the-new-fan-speed-sensors)) have low values on idle. If just one fan is on full speed but the other one is controlled according to fan curve, then you should [reset the BIOS and EC controller](#how-to-do-a-bios-upgrade-or-reset-the-embedded-controller-to-fix-a-problem).

## What is "advanced thermal optimization" in the BIOS?

You can change the fan curve and minimal fan speed that are programmed into the hardware:

- `off`: Turn off the fan if cold enough
- `level 1`: Minimal fan speed level 1
- `level 2`: Minimal fan speed level 2
- `level 3`: Minimal fan speed level 3

Also see: https://forums.lenovo.com/t5/Gaming-Laptops/Legion-7-Bios-What-is-advanced-thermal-optimization/m-p/5079357

## I don't use GNOME. How do I get a nice widget for changing the power mode?

The power mode can be changed using Fn+Q.

If you use KDE, the power mode can be changed from the "Battery And Brightness" icon.

If you don't need a GUI, you could [use the commandline](usage.md#modify-with-cli).

For other desktop environments:
This driver makes power mode changing available to tools like `power-profiles-daemon`.

First you should try changing from the terminal, see ["Powermode -> Modify with CLI"](usage.md#modify-with-cli). If it works, then install `power-profiles-daemon`.

A graphical GNOME applet uses `power-profiles-daemon` to change the power mode using software. It is not provided by this tool, but is a standard tool already integrated into GNOME.

For KDE, there is the graphical tool `powerdevil`, which also uses `power-profiles-daemon` internally.

If KDE only shows `balanced` and `performance` in `/sys/firmware/acpi/platform_profile_choices` but the Legion device (for example `/sys/devices/pci0000:00/0000:00:1f.0/PNP0C09:00/platform-profile/platform-profile-1/choices`) includes `quiet`, check whether `lenovo_wmi_gamezone` is also loaded. If both providers are active, the global profile choices are the intersection of both providers and quiet mode might disappear. In that case, unload or blacklist `lenovo_wmi_gamezone` and keep `legion_laptop` as the single provider for power mode.

Alternatively keep both drivers and let each do what the other cannot: load `legion_laptop` with `enable_platformprofile=0`, so it registers no platform-profile provider and leaves the power mode (`platform_profile`) and the power limits (`/sys/class/firmware-attributes/lenovo-wmi-other-*`) to the mainline drivers. Its own `powermode` and power-limit attributes stay available under the platform device; what the mainline drivers do not offer at all, and what you keep `legion_laptop` for, is the fan curve, the fan speeds and fan full speed. Put

```text
options legion_laptop enable_platformprofile=0
softdep legion_laptop pre: ideapad_laptop lenovo_wmi_gamezone lenovo_wmi_other lenovo_wmi_events lenovo_wmi_capdata
```

into `/etc/modprobe.d/legion_laptop.conf`; the `softdep` line loads the mainline drivers first so they bind the WMI devices both drivers list. The mainline `custom` profile is the same firmware mode as `powermode` 255; select it through `/sys/class/platform-profile/platform-profile-N/profile` of the device named `lenovo-wmi-gamezone`, because the legacy `/sys/firmware/acpi/platform_profile` file refuses `custom` by design. Verified on a Legion Pro 5 16IRX8 with kernel 7.2.

On the Legion Pro 7 16IAX10H (83F5, Q7CN) and the Legion 5 15IRX10 (83LY, QNCN) none of this is needed for the power limits: `legion_laptop` leaves the GameZone WMI device to `lenovo_wmi_gamezone` whatever the load order, so `/sys/class/firmware-attributes/lenovo-wmi-other-0` (PL1/PL2, cTGP, ...) works next to it with the default options. Both drivers then register a platform-profile provider with the same five choices, so no profile is lost from the global list.

## My Intel Legion is limited to about 30 W CPU power in every mode except custom. Why?

Check `cat /sys/class/powercap/intel-rapl-mmio:0/constraint_{0,1}_power_limit_uw`. On some firmware (for example the Legion Pro 7 16IAX10H, Q7CN) the CPU enforces this MMIO RAPL limit, which the BIOS sets to 30 W at boot. The firmware then writes it only when custom mode is entered, and leaves quiet/balanced/performance/extreme to Lenovo's software and Intel DTT on Windows. thermald's adaptive mode does not help: the firmware selects its per-mode targets through conditions that only Windows software sets, so thermald applies one fixed limit to all modes. `legion_laptop` exports the firmware's per-mode defaults in `cpu_longterm_powerlimit_defaults` / `cpu_shortterm_powerlimit_defaults` (e.g. `performance:145` / `performance:190`), and `legiond` applies them on every profile change when `cpu_powerlimit_sync=true` is set in `/etc/legion_linux/legiond.ini` (see `extra/service/legiond/README.org`); with the optional `double_*` keys it also switches to the firmware's lower combined-load CPU limits once the chassis sensors get hot, as Windows does (e.g. 145 W → 75 W in performance), leaving headroom for the GPU. Don't run thermald's power-limit control (e.g. `thermald --adaptive`) at the same time: both write the same MMIO limit and would override each other, at the latest on every 30 s `legiond-cpuset.timer` refresh. Also note that the WMI power-limit attributes (`legion_laptop`'s `cpu_longterm_powerlimit` / `cpu_shortterm_powerlimit` on models that show them, `lenovo-wmi-other`'s `ppt_pl1_spl` / `ppt_pl2_sppt` on the 16IAX10H) hold the values the firmware applies in custom mode; in the other modes they can differ from the enforced limit, so check the MMIO values above. Without legiond, entering custom mode once applies the custom PL1/PL2, which then stay in place until reboot. The GPU has its own limit: on these models enable NVIDIA's Dynamic Boost daemon (`sudo systemctl enable --now nvidia-powerd`, part of the NVIDIA driver). Without it the Legion Pro 7 16IAX10H's RTX 5090 is held at 95 W in every mode; with it, the limit is 150 W in performance/extreme and up to 175 W under load (check with `nvidia-smi -q -d POWER`).

## Screen brightness keys or `brightnessctl` do nothing on a hybrid-graphics (Intel + NVIDIA) Legion

In hybrid mode the internal panel is driven by the Intel GPU (`intel_backlight`), but the NVIDIA driver also registers `nvidia_0` for the dGPU's panel output, which is disconnected in that mode. `brightnessctl`, `swayosd` and similar tools default to the first device, `nvidia_0`, so their changes have no visible effect even though the brightness keys work (they arrive as `KEY_BRIGHTNESSUP/DOWN` from the ACPI "Video Bus"). Check with `brightnessctl -l` and name the device explicitly, e.g. `brightnessctl -d intel_backlight set 50%` or `swayosd-client --device intel_backlight --brightness +5`, in your key bindings and idle daemon. Seen on the Legion Pro 7 16IAX10H (OLED panel). In dGPU-only mode the panel moves to the NVIDIA GPU and `nvidia_0` is the right device.

## It almost works, but (some) temperature sensor/changing point in fan control or (some) fan speed is not working. What should I do?

First, try to [reset the embedded controller](#how-to-do-a-bios-upgrade-or-reset-the-embedded-controller-to-fix-a-problem) OR do a BIOS update/downgrade to reset everything.

## It does not work after a kernel update.

Option 1: Recompile/reinstall the module, see: [Permanent Install Instructions](installation.md#permanent-install-instruction).
Option 2: Use DKMS to automate this process for every kernel update, see: [Installing via DKMS](installation.md#installing-via-dkms)

## My screen is dimmed after a time of inactivity even if I disabled that in Ubuntu. How to fix that? (GNOME)

```bash
gsettings set org.gnome.settings-daemon.plugins.power idle-brightness 100
```

See: https://old.reddit.com/r/linuxquestions/comments/utle2w/ubuntu_2204_is_there_a_way_to_disable_screen/

## How to power down the dGPU while not in use and use the iGPU for power saving instead?

This describes _a way_ to configure and use it on Ubuntu using X11. It configures it such that
everything runs on iGPU if not otherwise selected.
- Check that Hybrid Mode is enabled in the BIOS.
- Check that X11 is used and not Wayland:
```bash
# It should output something like: "x11"
echo $XDG_SESSION_TYPE
```
- Install `prime` and select "on-demand". A restart might be needed:
```bash
sudo prime-select on-demand
```
- Check with `nvidia-smi` that no programs run on the dGPU:
```bash
sudo nvidia-smi
```
  Note that the one process `0   N/A  N/A  ***  G   /usr/lib/xorg/Xorg   4MiB` is ok. Moreover, note
  that running `nvidia-smi` powers up the GPU for some time.
- Allow `d3cold` mode:
```bash
# Note: Only one of the commands would work; depending on the path to the device which is your GPU
echo 1 > /sys/devices/pci0000\:00/0000\:00\:01.1/d3cold_allowed 
echo 1 > /sys/devices/pci0000\:00/0000\:00\:01.0/d3cold_allowed 
```
Check that GPU Runtime `D3` status is enabled:
```bash
sudo cat /proc/driver/nvidia/gpus/0000:01:00.0/power
```
- Check the current state of the GPU:
```bash
# Note: Only one of the commands would work; depending on the path to the device which is your GPU
# It should output "D3cold":
cat /sys/devices/pci0000\:00/0000\:00\:01.0/power_state
cat /sys/devices/pci0000\:00/0000\:00\:01.1/power_state 
```
- Run `nvidia-smi`, which powers the GPU up for some time. Check the `power_state` again. It should go to `D0` and then go to `D3cold` after some time. Compared to `nvidia-smi`, running `cat /sys/devices/pci0000\:00/0000\:00\:01.1/power_state ` does not seem to wake up the GPU.


```bash
sudo cat /proc/driver/nvidia/gpus/0000:01:00.0/power
```



## :question: Unanswered Questions

- What exactly is the third temperature? Currently, it is currently called IC Temperature.
- Is "quiet mode" suitable for gaming?
