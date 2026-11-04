# 常见问题解答

## 新增的温度传感器有哪些？

这些是由嵌入式控制器测量和使用的温度，只对风扇控制器有实际意义。它们由新的内核模块提供，其他情况下无法获取，因为这些数据是直接从嵌入式控制器读取的。

## 新增的风扇转速传感器有哪些？

这些传感器会报告风扇转速（单位为 rpm，转/分）。它们同样由新的内核模块提供，其他情况下无法获取，因为这些数据也是从嵌入式控制器读取的。

## 控制风扇转速使用了哪些温度？

会使用 CPU、GPU 和 “IC” 的温度。这些（通常）是额外的传感器，与未使用内核模块时系统报告的温度不同。尤其是 “IC” 温度的阈值可能设置得很低，会导致风扇几乎一直转。

## 为什么我的 CPU 和 GPU 温度很低但风扇仍然在转？

请参考上文，尤其是 “IC” 温度传感器的影响。

## 风扇转速会根据功耗变化吗？

据我所知，并没有这个情况。目前观察到的风扇控制只和温度有关。

## 为什么我的风扇不加速、从不停止或速度一直不变（使用过其他工具后）？

如果风扇速度一直比较恒定，可能是风扇控制器被锁定（通常称为锁定风扇转速）。你可以在 GUI（见[使用指南](usage.md)）中锁定/解锁风扇控制器。一般不建议锁定。进行 BIOS/UEFI 更新通常也会解锁，但请谨慎操作并建议做好 BIOS 备份。

如果风扇在高负载下始终没有加速，可能是风扇控制器被锁定（如上）。同时请检查 CPU（或 GPU）在负载下报告的温度是否确实升高。只有 “CPU Temperature”、“GPU Temperature” 和 “IC Temperature” 这三个温度会被用于风扇控制，这些温度是硬件风扇控制器内部实际用到的。

如果风扇从不停止，可能是你设置了很低的 CPU、GPU 或 IC 的最高温度阈值。许多机型即使在安静模式下也会有较低的温度阈值，导致风扇一直不会停止。你可以适当提高最低档位的温度阈值。

## 空闲时风扇很吵。

请参考上面相关说明。

## 浏览网页等轻量工作时风扇就启动了。

即使在浏览网页时，CPU 也可能会有短时间的负载，导致温度短暂升高从而风扇启动。你可以：

- 调整风扇曲线，特别是提高温度上限、增加加速时间
- 禁用 CPU 的加速模式（boost mode）
- 也可参考上面其它建议

## 报告的温度没有变化或看起来不正确。

请参考上面相关说明。

## 高负载下风扇转速还是不够快。

请参考上面相关说明。

## BIOS 更新后某些功能（如风扇控制）失效怎么办？

可能是 BIOS 更新过程中出现了问题。可以降级回旧版本测试，然后再重新升级，并再次检查当前版本下的功能是否正常。

## 如何升级 BIOS 或重置嵌入式控制器以修复问题？

最简单的方法是先降级到较旧版本，然后再升级回当前版本，并在旧版本下测试功能。  
你也可以尝试如下方式重置嵌入式控制器：

- 关闭笔记本，拔掉所有连接（充电器、USB 等）
- 按住电源键 60 秒不放；即使设备开机也要继续按住
- 60 秒后松开电源键
- 短按电源键开机

---

## 安静、平衡、高性能模式分别做了什么？

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

## 玩游戏时应该用平衡模式还是高性能模式？

两者在实际性能（FPS）上的差别很小。想追求极致性能就用高性能模式，日常推荐用平衡模式。

---

## 有一个风扇一直满速运转怎么办？

首先检查风扇曲线是否设置正确，确保不是配置错误。再检查用于风扇控制的温度（见 ["新增温度"](#新增的风扇转速传感器有哪些)）在空闲时是否过低。如果只有一个风扇满速，另一个能正常按曲线控制，建议[重置 BIOS 和 EC 控制器](#如何升级-bios-或重置嵌入式控制器以修复问题)。

---

## BIOS 里的“高级散热优化”是什么？

你可以更改硬件中预设的风扇曲线和最小风扇转速：

- `off`：足够冷时关闭风扇
- `level 1`：最小风扇转速等级 1
- `level 2`：最小风扇转速等级 2
- `level 3`：最小风扇转速等级 3

参考：https://forums.lenovo.com/t5/Gaming-Laptops/Legion-7-Bios-What-is-advanced-thermal-optimization/m-p/5079357

---

## 我不用 GNOME，如何获得切换电源模式的漂亮小部件？

你可以直接用 Fn+Q 切换电源模式。

如果你用 KDE，可以在“电池与亮度”图标处切换。

如果不需要 GUI，可以[使用命令行](usage.md#使用-cli-修改)。

其它桌面环境：
本驱动会将电源模式切换功能暴露给如 `power-profiles-daemon` 等工具。

建议先在终端测试（见 ["Powermode -> Modify with CLI"](usage.md#使用-cli-修改)），如可用，再安装 `power-profiles-daemon`。

GNOME 的图形小程序会用 `power-profiles-daemon` 以软件方式切换电源模式，这是 GNOME 的标准功能，并未由本工具提供。

对于 KDE，有图形工具 `powerdevil`，其内部同样利用 `power-profiles-daemon`。

如果 KDE 在 `/sys/firmware/acpi/platform_profile_choices` 中只显示 `balanced` 和 `performance`，但 Legion 设备（例如 `/sys/devices/pci0000:00/0000:00:1f.0/PNP0C09:00/platform-profile/platform-profile-1/choices`）包含 `quiet`，请检查是否同时加载了 `lenovo_wmi_gamezone`。如果两个驱动同时处于活动状态，全局可选模式会取两者的交集，quiet 模式可能会消失。此时可卸载或拉黑（blacklist）`lenovo_wmi_gamezone`，让 `legion_laptop` 成为唯一的电源模式提供者。

另一种做法是同时保留两个驱动、各司其职：以 `enable_platformprofile=0` 加载 `legion_laptop`，它便不再注册电源模式提供者，把电源模式（`platform_profile`）和功耗限制（`/sys/class/firmware-attributes/lenovo-wmi-other-*`）交给主线驱动。它自身的 `powermode` 与功耗限制属性仍在平台设备下可用；主线驱动完全不提供、也正是保留 `legion_laptop` 的原因，是风扇曲线、风扇转速和风扇全速。将

```text
options legion_laptop enable_platformprofile=0
softdep legion_laptop pre: ideapad_laptop lenovo_wmi_gamezone lenovo_wmi_other lenovo_wmi_events lenovo_wmi_capdata
```

写入 `/etc/modprobe.d/legion_laptop.conf`；`softdep` 行会先加载主线驱动，让它们先绑定两个驱动都声明的 WMI 设备。主线的 `custom` 配置与 `powermode` 255 是同一个固件模式；请通过名为 `lenovo-wmi-gamezone` 的设备的 `/sys/class/platform-profile/platform-profile-N/profile` 选择它，因为旧的 `/sys/firmware/acpi/platform_profile` 文件按设计拒绝 `custom`。已在 Legion Pro 5 16IRX8、内核 7.2 上验证。

在拯救者 Pro 7 16IAX10H（83F5，Q7CN）和拯救者 Legion 5 15IRX10（83LY，QNCN）上，功耗限制无需上述任何配置：无论加载顺序如何，`legion_laptop` 都会把 GameZone WMI 设备留给 `lenovo_wmi_gamezone`，因此使用默认选项时 `/sys/class/firmware-attributes/lenovo-wmi-other-0`（PL1/PL2、cTGP 等）也能与它共存。此时两个驱动都会注册电源模式提供者，且选项相同（五种），全局列表不会丢失任何模式。

## 我的 Intel 拯救者除自定义模式外，CPU 功耗都被限制在约 30 W，为什么？

查看 `cat /sys/class/powercap/intel-rapl-mmio:0/constraint_{0,1}_power_limit_uw`。在部分固件上（例如拯救者 Pro 7 16IAX10H，Q7CN），CPU 实际执行的是这个 MMIO RAPL 限制，BIOS 启动时将其设为 30 W；固件只在进入自定义模式时才写入它，安静/均衡/性能/狂暴模式交给 Windows 上的联想软件和 Intel DTT 处理。thermald 的 adaptive 模式也无济于事：固件通过只有 Windows 软件才会设置的条件来选择各模式的目标，因此 thermald 只会对所有模式套用同一个固定限制。`legion_laptop` 在 `cpu_longterm_powerlimit_defaults` / `cpu_shortterm_powerlimit_defaults` 中导出固件的各模式默认值（例如 `performance:145` / `performance:190`），在 `/etc/legion_linux/legiond.ini` 中设置 `cpu_powerlimit_sync=true` 后，`legiond` 会在每次切换电源模式时应用这些值（见 `extra/service/legiond/README.org`）；配置可选的 `double_*` 项后，它还会在机身传感器升温后像 Windows 一样切换到固件中较低的 CPU+GPU 同时负载限制（例如性能模式 145 W → 75 W），为 GPU 留出余量。不要同时运行 thermald 的功耗限制控制（例如 `thermald --adaptive`）：两者写入同一个 MMIO 限制，会互相覆盖，最迟在 `legiond-cpuset.timer` 每 30 秒刷新时发生。另外请注意，WMI 功耗限制属性（显示这些属性的机型上为 `legion_laptop` 的 `cpu_longterm_powerlimit` / `cpu_shortterm_powerlimit`，16IAX10H 上为 `lenovo-wmi-other` 的 `ppt_pl1_spl` / `ppt_pl2_sppt`）保存的是固件在自定义模式下应用的值；在其他模式下它们可能与实际执行的限制不同，请以上面的 MMIO 值为准。不使用 legiond 时，进入一次自定义模式即可应用自定义的 PL1/PL2，并在重启前一直保持。GPU 有自己的功耗限制：在这些机型上请启用 NVIDIA 的 Dynamic Boost 守护进程（`sudo systemctl enable --now nvidia-powerd`，随 NVIDIA 驱动提供）。未启用时，拯救者 Pro 7 16IAX10H 的 RTX 5090 在所有模式下都被限制在 95 W；启用后，性能/狂暴模式为 150 W，负载下最高 175 W（可用 `nvidia-smi -q -d POWER` 查看）。

## 混合显卡（Intel + NVIDIA）拯救者上屏幕亮度键或 `brightnessctl` 无效

在混合模式下，内屏由 Intel GPU 驱动（`intel_backlight`），但 NVIDIA 驱动还会为独显的屏幕输出注册 `nvidia_0`，而该输出在此模式下处于断开状态。`brightnessctl`、`swayosd` 等工具默认使用第一个设备 `nvidia_0`，因此即使亮度键本身正常（它们以 `KEY_BRIGHTNESSUP/DOWN` 的形式来自 ACPI "Video Bus"），调整也看不到任何效果。用 `brightnessctl -l` 查看，并在快捷键绑定和空闲守护进程中明确指定设备，例如 `brightnessctl -d intel_backlight set 50%` 或 `swayosd-client --device intel_backlight --brightness +5`。已在拯救者 Pro 7 16IAX10H（OLED 屏）上确认。在纯独显模式下内屏改由 NVIDIA GPU 驱动，此时 `nvidia_0` 才是正确的设备。

## 几乎都能用，但某些温度传感器/风扇控制节点或风扇转速无效，怎么办？

首先，尝试[重置嵌入式控制器](#如何升级-bios-或重置嵌入式控制器以修复问题)或进行 BIOS 升级/降级来重置所有设置。

---

## 内核升级后无法使用怎么办？

方案一：重新编译/安装内核模块，参见：[永久安装说明](installation.md#永久安装说明)。  
方案二：使用 DKMS 实现每次内核更新后自动安装，参见：[使用 DKMS 安装](installation.md#使用-dkms-安装)。

---

## 即使在 Ubuntu 里关闭了，屏幕在一段时间不用后还是会变暗，如何解决？（GNOME）

```bash
gsettings set org.gnome.settings-daemon.plugins.power idle-brightness 100
```

参考：https://old.reddit.com/r/linuxquestions/comments/utle2w/ubuntu_2204_is_there_a_way_to_disable_screen/

---

## 如何在不用 dGPU 时彻底关闭它，并只用 iGPU 实现省电？

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
